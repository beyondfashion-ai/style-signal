import argparse
import json
from pathlib import Path
import sys
import time

from .fetcher import FetcherNotInstalled, stealthy_fetch
from .registry import get_adapter, list_sources
from .schema import FetchResult, Query


def _print_json(payload: dict | list) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _query_from_args(args: argparse.Namespace) -> Query:
    return Query(
        source=args.source,
        category=args.category,
        keyword=args.keyword,
        gender=args.gender,
        sort=args.sort,
        limit=args.limit,
        curation=args.curation,
    )


def _default_raw_output(source: str) -> str:
    return str(Path("artifacts") / f"{source}-result.md")


def _failure(query: Query, error: str, message: str, raw_path: str | None = None, attempts: int = 1) -> FetchResult:
    return FetchResult(
        success=False,
        query=query,
        products=[],
        raw_path=raw_path,
        error=error,
        message=message,
        attempts=attempts,
    )


def _run_fetch_once(
    adapter,
    query: Query,
    raw_output: str,
    timeout_ms: int,
    scrapling_bin: str | None,
) -> tuple[bool, FetchResult]:
    try:
        url = adapter.build_url(query)
    except NotImplementedError as exc:
        return False, _failure(query, "MISSING_ARGS", str(exc), raw_output)
    except ValueError as exc:
        return False, _failure(query, "MISSING_ARGS", str(exc), raw_output)

    try:
        fetch_ok, file_size, raw_text = stealthy_fetch(
            url,
            raw_output,
            timeout_ms=timeout_ms,
            scrapling_bin=scrapling_bin,
        )
    except FetcherNotInstalled as exc:
        return False, _failure(query, "NO_OUTPUT", str(exc), raw_output)

    if not raw_text:
        return False, FetchResult(
            success=False,
            query=query,
            products=[],
            raw_path=raw_output,
            error="NO_OUTPUT",
            message="크롤링 결과 파일이 생성되지 않았습니다.",
            file_size=file_size,
        )

    block_error = adapter.detect_block(raw_text, file_size)
    if block_error:
        return False, FetchResult(
            success=False,
            query=query,
            products=[],
            raw_path=raw_output,
            error=block_error,
            message="크롤링 결과가 차단되었거나 비어 있습니다.",
            file_size=file_size,
        )

    if not fetch_ok:
        return False, FetchResult(
            success=False,
            query=query,
            products=[],
            raw_path=raw_output,
            error="NETWORK",
            message="scrapling fetch returned a non-zero exit code.",
            file_size=file_size,
        )

    try:
        products = adapter.parse(raw_text, query)
    except Exception as exc:
        return False, FetchResult(
            success=False,
            query=query,
            products=[],
            raw_path=raw_output,
            error="PARSE_FAILED",
            message=str(exc),
            file_size=file_size,
        )

    if not products:
        return False, FetchResult(
            success=False,
            query=query,
            products=[],
            raw_path=raw_output,
            error="PARSE_FAILED",
            message="No products parsed from fetched markdown.",
            file_size=file_size,
        )

    return True, FetchResult(
        success=True,
        query=query,
        products=products,
        raw_path=raw_output,
        file_size=file_size,
    )


def cmd_list_sources(_args: argparse.Namespace) -> int:
    _print_json({"sources": list_sources()})
    return 0


def cmd_describe(args: argparse.Namespace) -> int:
    try:
        adapter = get_adapter(args.source)
    except ValueError as exc:
        _print_json({"success": False, "error": "UNKNOWN_SOURCE", "message": str(exc)})
        return 1

    _print_json(adapter.describe())
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    query = _query_from_args(args)
    raw_output = args.raw_output or _default_raw_output(query.source)
    Path(raw_output).parent.mkdir(parents=True, exist_ok=True)

    try:
        adapter = get_adapter(query.source)
    except ValueError as exc:
        result = _failure(query, "MISSING_ARGS", str(exc), raw_output)
        _print_json(result.to_json())
        return 1

    ok, result = _run_fetch_once(adapter, query, raw_output, args.timeout_ms, args.scrapling_bin)
    attempts = 1

    if not ok and args.retry_on_block and result.error == "BLOCKED":
        time.sleep(30)
        attempts = 2
        ok, result = _run_fetch_once(adapter, query, raw_output, args.timeout_ms, args.scrapling_bin)

    result.attempts = attempts
    _print_json(result.to_json())
    return 0 if result.success else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="style-signal")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-sources")
    list_parser.set_defaults(func=cmd_list_sources)

    describe_parser = subparsers.add_parser("describe")
    describe_parser.add_argument("--source", required=True)
    describe_parser.set_defaults(func=cmd_describe)

    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("--source", required=True)
    fetch_parser.add_argument("--keyword")
    fetch_parser.add_argument("--category")
    fetch_parser.add_argument("--curation", choices=["top100"])
    fetch_parser.add_argument("--gender", choices=["men", "women", "unisex"])
    fetch_parser.add_argument(
        "--sort",
        default="popular",
        choices=["popular", "recommend", "new", "price_asc", "price_desc", "premium_asc"],
    )
    fetch_parser.add_argument("--limit", type=int, default=40)
    fetch_parser.add_argument("--raw-output")
    fetch_parser.add_argument("--timeout-ms", type=int, default=40000)
    fetch_parser.add_argument("--scrapling-bin")
    fetch_parser.add_argument("--retry-on-block", action="store_true")
    fetch_parser.set_defaults(func=cmd_fetch)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
