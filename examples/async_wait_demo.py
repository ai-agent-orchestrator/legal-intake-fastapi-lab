"""No API key, network, or dependencies. Compare sequential and concurrent waits.

This is a learning example, not the planned Legal Intake application.
"""
import asyncio
from time import perf_counter


async def fake_ai(question: str) -> str:
    print(f"  start: {question}")
    await asyncio.sleep(1)
    print(f"  end:   {question}")
    return f"fake answer: {question}"


async def main() -> None:
    questions = ["A", "B", "C"]
    print("1) Sequential await: start next task after the previous one finishes")
    started = perf_counter()
    sequential = []
    for question in questions:
        sequential.append(await fake_ai(question))
    print(f"Sequential: {perf_counter() - started:.2f}s\n")

    print("2) Concurrent waits: schedule independent tasks with gather")
    started = perf_counter()
    concurrent = await asyncio.gather(*(fake_ai(q) for q in questions))
    print(f"Concurrent: {perf_counter() - started:.2f}s")
    assert sequential == concurrent
    print("Same fake answers. No OpenAI calls. Timing is illustrative, not a server benchmark.")


if __name__ == "__main__":
    asyncio.run(main())
