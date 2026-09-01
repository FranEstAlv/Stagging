from __future__ import annotations


class _JobQueueRecorder:
    """Envoltorio de app.job_queue usado solo durante install_modulo(app,
    contexto) -- graba cada Job programado para poder cancelarlo
    (job.schedule_removal()) cuando el modulo se desactiva. Todo lo demas
    (get_jobs_by_name, etc.) se delega tal cual al job_queue real."""

    def __init__(self, job_queue, sink: list):
        self._jq = job_queue
        self._sink = sink

    def _grabar(self, job):
        self._sink.append(job)
        return job

    def run_once(self, *args, **kwargs):
        return self._grabar(self._jq.run_once(*args, **kwargs))

    def run_repeating(self, *args, **kwargs):
        return self._grabar(self._jq.run_repeating(*args, **kwargs))

    def run_daily(self, *args, **kwargs):
        return self._grabar(self._jq.run_daily(*args, **kwargs))

    def run_monthly(self, *args, **kwargs):
        return self._grabar(self._jq.run_monthly(*args, **kwargs))

    def __getattr__(self, nombre):
        return getattr(self._jq, nombre)


class AppRecorder:
    """Envoltorio de 'app' usado solo durante install_modulo(app, contexto)
    -- graba cada handler agregado (para poder app.remove_handler(...)
    despues sin reimportar el modulo) y expone un job_queue que graba jobs
    de la misma forma. Todo lo demas (bot, bot_data, etc.) se delega tal
    cual al app real -- un modulo no nota la diferencia."""

    def __init__(self, app, handlers_sink: list, jobs_sink: list):
        self._app = app
        self._handlers_sink = handlers_sink
        self._jobs_sink = jobs_sink

    def add_handler(self, handler, group: int = 0) -> None:
        self._app.add_handler(handler, group)
        self._handlers_sink.append((handler, group))

    @property
    def job_queue(self):
        return _JobQueueRecorder(self._app.job_queue, self._jobs_sink)

    def __getattr__(self, nombre):
        return getattr(self._app, nombre)


__all__ = ["AppRecorder"]
