from __future__ import annotations

import logging
import time
from typing import Callable, Sequence
from uuid import UUID

from ai_meeting_companion.core.agent import BaseAgent
from ai_meeting_companion.core.bus import Bus
from ai_meeting_companion.memory.session_memory import SessionMemory
from ai_meeting_companion.session.logger import SessionLogger
from ai_meeting_companion.session.store import SessionStore

log = logging.getLogger(__name__)

AgentFactory = Callable[[Bus, SessionMemory], Sequence[BaseAgent]]


class Orchestrator:
    """Owns one meeting session: opens the thread, wires the bus, starts and stops the agents."""

    def __init__(self, store: SessionStore, agent_factory: AgentFactory, title: str | None = None) -> None:
        self.store = store
        self.bus = Bus()
        self.memory = SessionMemory()
        self.bus.add_tap(self.memory.record)  # one timeline shared by all agents
        self.title = title
        self._agent_factory = agent_factory
        self._agents: list[BaseAgent] = []
        self._logger: SessionLogger | None = None
        self.thread_id: UUID | None = None

    def start(self) -> UUID:
        thread = self.store.create_thread(title=self.title)
        self.thread_id = thread.id
        # The logger subscribes before anything can publish, so no event is missed.
        self._logger = SessionLogger(self.bus, self.store, thread.id)
        self._logger.start()
        self._agents = list(self._agent_factory(self.bus, self.memory))
        for agent in self._agents:
            agent.start()
        return thread.id

    def stop(self) -> None:
        try:
            for agent in self._agents:
                try:
                    agent.stop()
                except Exception:
                    log.exception("failed to stop %s", agent.name)
            if self._logger is not None:
                self._logger.stop()
                self._logger.drain()
        except KeyboardInterrupt:
            log.warning("interrupted during shutdown; closing the session now")
        finally:
            # Always mark the session ended, even if shutdown was cut short.
            if self.thread_id is not None:
                self.store.end_thread(self.thread_id)

    def run_until_interrupted(self) -> UUID:
        thread_id = self.start()
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            print("\nStopping and saving the session...", flush=True)
            self.stop()
        return thread_id
