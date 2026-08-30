import datetime
import logging
from fastapi import FastAPI, HTTPException
import inngest
import inngest.fast_api
import uuid


app = FastAPI()
reports: dict[str, dict] = {}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/reports", status_code=202)
async def create_report(body: dict):
    topic = body.get("topic")
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")

    report_id = str(uuid.uuid4())
    reports[report_id] = {"id": report_id, "topic": topic, "status": "pending"}

    await inngest_client.send(
        inngest.Event(name="report/requested", data={"id": report_id, "topic": topic})
    )

    return {"id": report_id, "status": "pending"}


@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    report = reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return report

inngest_client = inngest.Inngest(
    app_id="report-api",
    logger=logging.getLogger("uvicorn"),
)

@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)

async def say_hello(ctx: inngest.Context) -> str:
    await ctx.step.sleep("wait-a-bit", datetime.timedelta(seconds=5))
    return "Hello from the background!"

@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2, 
)
async def make_report(ctx: inngest.Context) -> None:
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    await ctx.step.sleep("do-the-slow-work", datetime.timedelta(seconds=8))

    def build_report():
        if topic == "fail":
            raise Exception("The report oven is broken!")
        result = f"A thorough, deeply researched report about {topic}."
        reports[report_id]["status"] = "done"
        reports[report_id]["result"] = result
        return result

    try:
        await ctx.step.run("build-report", build_report)
    except Exception:
        reports[report_id]["status"] = "failed"
        raise

@inngest_client.create_function(
    fn_id="heartbeat",
    trigger=inngest.TriggerCron(cron="* * * * *"), 
)
async def heartbeat(ctx: inngest.Context) -> None:
    counts = {"pending": 0, "done": 0, "failed": 0}
    for report in reports.values():
        status = report.get("status", "pending")
        counts[status] = counts.get(status, 0) + 1

    ctx.logger.info(
        f"Heartbeat: {counts['pending']} pending, "
        f"{counts['done']} done, {counts['failed']} failed"
    )

inngest.fast_api.serve(app, inngest_client, [say_hello, make_report, heartbeat])