import asyncio
import signal
import sys

COMMANDS = [
    ("backend", ["python3", "src/backend/main.py"]),
    ("frontend", ["python3", "src/frontend/main.py"]),
]


async def stream(prefix, stream):
    while line := await stream.readline():
        sys.stdout.write(f"[{prefix}] {line.decode()}")
        sys.stdout.flush()


async def run(name, cmd):
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await asyncio.gather(stream(name, proc.stdout), stream(name, proc.stderr))
    return await proc.wait()


async def main():
    tasks = [asyncio.create_task(run(name, cmd)) for name, cmd in COMMANDS]

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: [t.cancel() for t in tasks])

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
