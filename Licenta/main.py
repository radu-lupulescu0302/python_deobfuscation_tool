import argparse
import os
import glob

from deobfuscator.pipeline import HybridDeobfuscator
from deobfuscator.ioc_extractor import IOCExtractor
from deobfuscator.behavior_profiler import BehaviorProfiler
from deobfuscator import stats as _stats


def _process_one(path: str, out_path: str, static_only: bool) -> HybridDeobfuscator:
    with open(path, encoding="utf-8", errors="ignore") as f:
        source = f.read()
    deobf = HybridDeobfuscator(use_dynamic=not static_only)
    result = deobf.deobfuscate(source, path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result)
    deobf.metrics.print_report()
    print(f"Saved: {out_path}")
    return deobf


def _batch(input_dir: str, out_dir: str, static_only: bool) -> None:
    files = sorted(glob.glob(os.path.join(input_dir, "*.py")))
    if not files:
        print(f"No .py files found in {input_dir}")
        return

    os.makedirs(out_dir, exist_ok=True)
    print(f"[BATCH MODE] {len(files)} file(s) in '{input_dir}'  ->  '{out_dir}'\n")

    agg_ioc = IOCExtractor()
    agg_techniques: dict[str, int] = {}
    results: list[tuple[str, str]] = []

    for path in files:
        fname = os.path.basename(path)
        out_path = os.path.join(out_dir, f"clean_{fname}")
        sep = "=" * 60
        print(f"\n{sep}\n[FILE] {fname}\n{sep}")
        try:
            deobf = _process_one(path, out_path, static_only)
            # Merge IOC hits into aggregate extractor
            for cat, vals in deobf.ioc.hits.items():
                for v in vals:
                    if v not in agg_ioc.hits[cat]:
                        agg_ioc.hits[cat].append(v)
            for entry in deobf.ioc.suspicious_calls:
                agg_ioc._add_suspicious(entry["text"], f"{fname}:{entry['line']}")
            # Merge technique counts
            for tech, cnt in _stats.get_counts().items():
                agg_techniques[tech] = agg_techniques.get(tech, 0) + cnt
            results.append((fname, "OK"))
        except Exception as exc:
            results.append((fname, f"ERROR: {exc}"))
            print(f"  [!] Failed: {exc}")

    # ── Aggregate report ──────────────────────────────────────────────────────
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"BATCH SUMMARY  ({len(files)} file(s) processed)")
    print(sep)

    print("\n--- Results ---")
    for fname, status in results:
        tag = "OK  " if status == "OK" else "FAIL"
        print(f"  [{tag}] {fname}  ({status})")

    if agg_techniques:
        print("\n--- Obfuscation Techniques (all files) ---")
        for tech, cnt in sorted(agg_techniques.items(), key=lambda x: -x[1]):
            print(f"  {tech:<35} x{cnt}")

    agg_ioc.print_report()

    behaviors = BehaviorProfiler().profile(agg_ioc, agg_techniques)
    BehaviorProfiler().print_report(behaviors)

    print(f"\nDeobfuscated files saved to: {out_dir}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hybrid Python Malware Deobfuscator")
    parser.add_argument(
        "path", help="Obfuscated .py file  OR  directory of .py files (batch mode)"
    )
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output file (single mode) or output directory (batch mode). "
             "Defaults: 'deobfuscated.py' / 'deobfuscated_batch/'",
    )
    args = parser.parse_args()

    if os.path.isdir(args.path):
        _batch(args.path, args.output or "deobfuscated_batch", args.static_only)
    else:
        out = args.output or "deobfuscated.py"
        _process_one(args.path, out, args.static_only)


if __name__ == "__main__":
    main()
