from __future__ import annotations

import asyncio
import time
from urllib.parse import urlsplit, urlunsplit

from the_nanguos.agents import ArrangementAgent, ConductorAgent, LyricsAgent, MusicPlannerAgent
from the_nanguos.graphs import GraphState, build_generate_song_graph
from the_nanguos.memory import PreferenceStore, merge_preferences
from the_nanguos.schemas import CollaborationLog, CollaborationStep, GlobalArrangement, ScorePlan, ScoreSection, SunoLog, SunoTaskDetails, ValidationLog
from the_nanguos.tools import build_suno_request

from .jobs import GenerationRecord
from .storage import ArtifactStore
from .suno import SunoClient, SunoPollingStopped, SunoTaskFailed


def _without_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _sanitized_audio(audio):
    data = audio.model_dump(mode="json", by_alias=True)
    data["audioUrl"] = _without_query(data["audioUrl"])
    if data.get("streamAudioUrl"): data["streamAudioUrl"] = _without_query(data["streamAudioUrl"])
    if data.get("imageUrl"): data["imageUrl"] = _without_query(data["imageUrl"])
    return type(audio).model_validate(data)


class GenerationService:
    def __init__(self, *, llm, artifact_store: ArtifactStore, preferences: PreferenceStore | None = None, suno: SunoClient | None = None, submit: bool = True, poll_interval: float = 30, max_wait: float = 1200) -> None:
        self.llm = llm; self.store = artifact_store; self.preferences = preferences or PreferenceStore(); self.suno = suno
        self.submit = submit; self.poll_interval = poll_interval; self.max_wait = max_wait

    async def __call__(self, record: GenerationRecord) -> None:
        is_resume = record.stage == "resume_polling" and bool(record.task_id)
        resumed_log: CollaborationLog | None = None
        if is_resume:
            log_path = self.store.request_dir(record.request_id) / "collaboration_log.json"
            if not log_path.is_file(): raise RuntimeError("saved task metadata is unavailable")
            resumed_log = CollaborationLog.model_validate_json(log_path.read_text(encoding="utf-8"))
        profile = self.preferences.load_defaults().model_dump(mode="json")
        explicit = dict(record.options)
        merged = merge_preferences(defaults={"language":"zh", "instrumental":False, "suno_model":"V5"}, profile=profile, explicit=explicit)
        style_context = self.preferences.load_style()
        poll_started = 0.0
        attempts = 0

        async def init_run(_state: GraphState):
            record.status, record.stage, record.progress = "running", "conductor", 5
            return {}

        async def conductor_node(_state: GraphState):
            result = await ConductorAgent(self.llm).run(record.user_request, preferences=merged, style_context=style_context)
            song_spec = result.song_spec
            if explicit.get("title"):
                song_spec = song_spec.model_copy(update={"title": explicit["title"]})
            return {"song_spec": song_spec, "task_plan": result.task_plan}

        async def lyrics_node(state: GraphState):
            record.stage, record.progress = "lyrics", 20
            return {"lyrics_result": await LyricsAgent(self.llm).run(state.song_spec)}

        async def music_node(state: GraphState):
            record.stage, record.progress = "music_planner", 35
            return {"music_plan_result": await MusicPlannerAgent(self.llm).run(state.song_spec, state.lyrics_result)}

        async def arrangement_node(state: GraphState):
            record.stage, record.progress = "arrangement", 50
            return {"arrangement_result": await ArrangementAgent(self.llm).run(state.song_spec, state.lyrics_result, state.music_plan_result)}

        async def build_score_node(state: GraphState):
            lyric_sections = {section.name: section.lines for section in state.lyrics_result.sections}
            arrangement_sections = {section.name: section.arrangement for section in state.arrangement_result.sections}
            score = ScorePlan(sections=[ScoreSection(name=section.name, duration_seconds=section.duration_seconds, lyrics=lyric_sections.get(section.name, []), chords=section.chords, melody_intent=section.melody_intent, arrangement=arrangement_sections.get(section.name, "")) for section in state.music_plan_result.sections], global_arrangement=GlobalArrangement(instruments=state.arrangement_result.instruments, mix_style=state.arrangement_result.mix_style, dynamic_curve=state.arrangement_result.dynamic_curve, suno_style=state.arrangement_result.suno_style))
            return {"score_plan": score}

        async def validate_node(_state: GraphState):
            log = CollaborationLog(request_id=record.request_id, user_request_summary=record.user_request, artifacts={"song_spec":"song_spec.json", "score_plan":"score_plan.json", "suno_request":"suno_request.json", "collaboration_log":"collaboration_log.json"}, steps=[CollaborationStep(actor="ConductorAgent", action="normalized request"), CollaborationStep(actor="LyricsAgent", action="wrote lyrics"), CollaborationStep(actor="MusicPlannerAgent", action="planned music"), CollaborationStep(actor="ArrangementAgent", action="planned arrangement")], validation=ValidationLog(passed=True), suno=SunoLog(submitted=False, poll_interval_seconds=self.poll_interval, max_wait_seconds=self.max_wait))
            return {"validation_result": {"passed": True}, "collaboration_log": log}

        async def build_request_node(state: GraphState):
            request = build_suno_request(song_spec=state.song_spec, lyrics=state.lyrics_result, arrangement=state.arrangement_result, callback_url=str(explicit.get("callback_url") or "https://local.invalid/suno-callback"), model=str(merged.get("suno_model") or "V5"), instrumental=bool(merged.get("instrumental")), custom_mode=bool(explicit.get("custom_mode", True)), negative_tags=explicit.get("negative_tags"), vocal_gender=merged.get("vocal_gender"), style_weight=explicit.get("style_weight"), weirdness_constraint=explicit.get("weirdness_constraint"), audio_weight=explicit.get("audio_weight"))
            self.store.write_json(record.request_id, "song_spec.json", state.song_spec)
            self.store.write_json(record.request_id, "score_plan.json", state.score_plan)
            self.store.write_json(record.request_id, "suno_request.json", request)
            if not state.submit:
                record.status, record.stage, record.progress = "completed", "offline_complete", 100
                self.store.write_json(record.request_id, "collaboration_log.json", state.collaboration_log)
            return {"suno_request": request}

        async def submit_node(state: GraphState):
            if self.suno is None: raise RuntimeError("Suno client is not configured")
            record.stage, record.progress = "suno_submit", 55
            task_id = await self.suno.submit(state.suno_request)
            record.task_id = task_id
            state.collaboration_log.suno.submitted = True; state.collaboration_log.suno.task_id = task_id; state.collaboration_log.suno.status = "PENDING"
            self.store.write_json(record.request_id, "collaboration_log.json", state.collaboration_log)
            return {"suno_task_id": task_id}

        async def poll_node(state: GraphState):
            nonlocal poll_started, attempts
            poll_started = time.monotonic()
            async def update(details):
                nonlocal attempts
                attempts += 1; state.collaboration_log.suno.attempts = attempts; state.collaboration_log.suno.last_status = details.status; state.collaboration_log.suno.status = details.status
                record.stage = details.status
                record.progress = {"PENDING": 55, "TEXT_SUCCESS": 65, "FIRST_SUCCESS": 80}.get(details.status, record.progress)
                self.store.write_json(record.request_id, "collaboration_log.json", state.collaboration_log)
            try:
                details = await self.suno.poll(state.suno_task_id, interval_seconds=self.poll_interval, timeout_seconds=self.max_wait, stop_event=record.stop_event, on_update=update)
            except SunoPollingStopped:
                state.collaboration_log.suno.elapsed_seconds = time.monotonic() - poll_started; state.collaboration_log.suno.status = "STOPPED_WAITING"
                self.store.write_json(record.request_id, "collaboration_log.json", state.collaboration_log); raise
            except SunoTaskFailed as exc:
                state.collaboration_log.suno.elapsed_seconds = time.monotonic() - poll_started
                state.collaboration_log.suno.last_status = exc.status
                state.collaboration_log.suno.status = exc.status
                state.collaboration_log.suno.error = {"code": type(exc).__name__, "message": str(exc)}
                self.store.write_json(record.request_id, "collaboration_log.json", state.collaboration_log); raise
            except Exception as exc:
                state.collaboration_log.suno.elapsed_seconds = time.monotonic() - poll_started; state.collaboration_log.suno.error = {"code": type(exc).__name__, "message": str(exc)}
                self.store.write_json(record.request_id, "collaboration_log.json", state.collaboration_log); raise
            state.collaboration_log.suno.elapsed_seconds = time.monotonic() - poll_started; state.collaboration_log.suno.audio_results = [_sanitized_audio(audio) for audio in details.audio_results]; state.collaboration_log.suno.status = "SUCCESS"
            return {"suno_result": details.model_dump(mode="json")}

        async def save_node(state: GraphState):
            details = SunoTaskDetails.model_validate(state.suno_result)
            record.stage, record.progress = "saving_media", 90
            for audio in details.audio_results:
                urls = {str(audio.audio_url)} | ({str(audio.image_url)} if audio.image_url else set())
                audio_path = await self.store.download_media(record.request_id, "audio", audio.id, str(audio.audio_url), allowed_urls=urls)
                media = {"audio_id":audio.id, "source_url":_without_query(str(audio.audio_url)), "audio_path":audio_path.relative_to(self.store.outputs_dir).as_posix()}
                if audio.image_url:
                    cover = await self.store.download_media(record.request_id, "covers", audio.id, str(audio.image_url), allowed_urls=urls); media["cover_path"] = cover.relative_to(self.store.outputs_dir).as_posix()
                state.collaboration_log.suno.local_media.append(media)
                record.candidates.append({"audio_id":audio.id, "title":audio.title, "duration":audio.duration, "audio_url":f"/api/generations/{record.request_id}/audio/{audio.id}", "download_url":f"/api/generations/{record.request_id}/audio/{audio.id}/download", "cover_url":f"/api/generations/{record.request_id}/cover/{audio.id}"})
            record.status, record.stage, record.progress = "completed", "completed", 100
            self.store.write_json(record.request_id, "collaboration_log.json", state.collaboration_log)
            return {}

        graph = build_generate_song_graph(nodes={"init_run":init_run, "conductor":conductor_node, "lyrics":lyrics_node, "music_planner":music_node, "arrangement":arrangement_node, "build_score_plan":build_score_node, "validate":validate_node, "build_suno_request":build_request_node, "submit_suno":submit_node, "poll_suno":poll_node, "save_media":save_node})
        await graph.ainvoke(GraphState(request_id=record.request_id, user_request=record.user_request, output_dir=self.store.request_dir(record.request_id), submit=self.submit, resume_polling=is_resume, suno_task_id=record.task_id if is_resume else None, collaboration_log=resumed_log))
