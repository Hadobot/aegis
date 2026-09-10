import asyncio
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph_pipeline import AegisPipeline


async def run_evaluation():
    pipeline = AegisPipeline()

    # Load gold set
    with open("eval/gold_set.json", "r") as f:
        gold_set = json.load(f)

    results = []
    correct = 0
    total = len(gold_set)

    print(f"Running evaluation on {total} test cases...\n")

    for case in gold_set:
        start = time.time()

        try:
            result = await pipeline.analyze(prompt=case["input"])
            elapsed = (time.time() - start) * 1000

            predicted_action = result.get("action", "unknown")
            predicted_threat = result.get("threat_type", "none")

            # Check if correct
            action_correct = predicted_action == case["expected_action"]
            threat_correct = predicted_threat == case["expected_threat"]
            is_correct = action_correct and threat_correct

            if is_correct:
                correct += 1

            results.append({
                "id": case["id"],
                "input": case["input"][:50] + "..." if len(case["input"]) > 50 else case["input"],
                "expected_action": case["expected_action"],
                "predicted_action": predicted_action,
                "expected_threat": case["expected_threat"],
                "predicted_threat": predicted_threat,
                "correct": is_correct,
                "latency_ms": round(elapsed, 1)
            })

            status = "PASS" if is_correct else "FAIL"
            print(f"  [{status}] {case['id']}: {predicted_action} (expected {case['expected_action']})")

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            results.append({
                "id": case["id"],
                "input": case["input"][:50],
                "error": str(e),
                "correct": False,
                "latency_ms": round(elapsed, 1)
            })
            print(f"  [ERROR] {case['id']}: {str(e)[:50]}")

    # Calculate metrics
    accuracy = correct / total if total > 0 else 0

    # Separate attack vs benign accuracy
    attack_cases = [r for r in results if r.get("expected_action") == "block"]
    benign_cases = [r for r in results if r.get("expected_action") == "allow"]

    attack_correct = sum(1 for r in attack_cases if r.get("correct"))
    benign_correct = sum(1 for r in benign_cases if r.get("correct"))

    attack_detection_rate = attack_correct / len(attack_cases) if attack_cases else 0
    benign_pass_rate = benign_correct / len(benign_cases) if benign_cases else 0

    avg_latency = sum(r.get("latency_ms", 0) for r in results) / len(results) if results else 0

    # Print summary
    print(f"\n{'='*60}")
    print(f"EVALUATION RESULTS")
    print(f"{'='*60}")
    print(f"Total cases:     {total}")
    print(f"Correct:         {correct}/{total}")
    print(f"Accuracy:        {accuracy:.1%}")
    print(f"Attack detection: {attack_detection_rate:.1%} ({attack_correct}/{len(attack_cases)})")
    print(f"Benign pass rate: {benign_pass_rate:.1%} ({benign_correct}/{len(benign_cases)})")
    print(f"Avg latency:     {avg_latency:.1f}ms")
    print(f"{'='*60}")

    # Save results
    os.makedirs("eval/results", exist_ok=True)
    with open("eval/results/latest.json", "w") as f:
        json.dump({
            "summary": {
                "total": total,
                "correct": correct,
                "accuracy": accuracy,
                "attack_detection_rate": attack_detection_rate,
                "benign_pass_rate": benign_pass_rate,
                "avg_latency_ms": avg_latency
            },
            "cases": results
        }, f, indent=2)

    print(f"\nResults saved to eval/results/latest.json")

    # Fail if below threshold
    if accuracy < 0.85:
        print(f"\nFAIL: Accuracy {accuracy:.1%} is below 85% threshold")
        sys.exit(1)
    else:
        print(f"\nPASS: Accuracy {accuracy:.1%} meets threshold")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_evaluation())
