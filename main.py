import argparse
import asyncio
import importlib.util
from pathlib import Path
import re
import subprocess
import sys


DEFAULT_INPUT_HTML = Path("matrix_minimal_carousel.html")
DEFAULT_OUTPUT_DIR = Path("slides_output")
VIEW_W = 420
VIEW_H = 525
SCALE = 1080 / 420
FONT_WAIT_MS = 3000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export each slide from an Instagram-style HTML carousel as a PNG image."
    )
    parser.add_argument(
        "html",
        nargs="?",
        help="Input HTML file. If omitted, the default example file or the only HTML file in this folder is used.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Folder where exported PNG files will be saved. Default: slides_output",
    )
    parser.add_argument(
        "--font-wait-ms",
        type=int,
        default=FONT_WAIT_MS,
        help="Extra wait time before taking screenshots. Default: 3000",
    )
    return parser.parse_args()


def format_command(command: list[str]) -> str:
    return " ".join(f'"{part}"' if " " in part else part for part in command)


def run_setup_command(command: list[str], description: str) -> None:
    print(description)
    try:
        subprocess.check_call(command)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"{description} failed.\nRun this command manually and try again:\n{format_command(command)}"
        ) from exc


def ensure_playwright_package() -> None:
    if importlib.util.find_spec("playwright") is not None:
        return

    requirements_file = Path(__file__).with_name("requirements.txt")
    if requirements_file.exists():
        run_setup_command(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            "Playwright was not found. Installing Python dependencies...",
        )
        return

    run_setup_command(
        [sys.executable, "-m", "pip", "install", "playwright"],
        "Playwright was not found. Installing the Playwright package...",
    )


def install_chromium() -> None:
    run_setup_command(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        "Chromium was not found. Downloading the browser for Playwright...",
    )


def resolve_input_html(html_argument: str | None) -> Path:
    if html_argument:
        html_path = Path(html_argument)
        if not html_path.is_absolute():
            html_path = Path.cwd() / html_path
        html_path = html_path.resolve()
        if not html_path.exists():
            raise FileNotFoundError(f"HTML file not found: {html_path}")
        return html_path

    default_html = (Path.cwd() / DEFAULT_INPUT_HTML).resolve()
    if default_html.exists():
        return default_html

    html_files = sorted(Path.cwd().glob("*.html"))
    if len(html_files) == 1:
        return html_files[0].resolve()

    if not html_files:
        raise FileNotFoundError(
            "No HTML file was found in this folder. Add an HTML file or run: python main.py your-file.html"
        )

    available_files = ", ".join(path.name for path in html_files)
    raise FileNotFoundError(
        f"Multiple HTML files were found: {available_files}\nChoose one explicitly, for example: python main.py {html_files[0].name}"
    )


def get_output_stem(input_html: Path) -> str:
    sanitized_name = re.sub(r"[^A-Za-z0-9._-]+", "_", input_html.stem).strip("._-")
    return sanitized_name or "export"


def get_next_run_number(output_dir: Path, output_stem: str) -> int:
    run_numbers = []
    has_base_exports = False
    single_run_pattern = re.compile(rf"{re.escape(output_stem)}_(\d+)\.png")
    multi_run_pattern = re.compile(rf"{re.escape(output_stem)}_(\d+)_(\d+)\.png")

    for png_file in output_dir.glob("*.png"):
        match = multi_run_pattern.fullmatch(png_file.name)
        if match:
            run_numbers.append(int(match.group(1)))
            continue

        if single_run_pattern.fullmatch(png_file.name):
            has_base_exports = True

    if run_numbers:
        return max(run_numbers) + 1

    if has_base_exports:
        return 2

    return 1


def build_output_path(output_dir: Path, output_stem: str, run_number: int, slide_number: int) -> Path:
    if run_number == 1:
        filename = f"{output_stem}_{slide_number}.png"
    else:
        filename = f"{output_stem}_{run_number}_{slide_number}.png"
    return output_dir / filename


async def prepare_page(page, html_content: str, font_wait_ms: int) -> int:
    await page.set_content(html_content, wait_until="networkidle")

    if font_wait_ms > 0:
        print(f"Waiting {font_wait_ms / 1000:g} seconds for fonts to load...")
        await page.wait_for_timeout(font_wait_ms)

    # Remove the Instagram chrome so screenshots only capture the slide area.
    await page.evaluate("""() => {
        document.querySelectorAll('.ig-header,.ig-dots,.ig-actions,.ig-caption')
            .forEach(el => el.style.display = 'none');

        const frame = document.querySelector('.ig-frame');
        if (!frame) {
            throw new Error("Missing .ig-frame in the HTML file.");
        }
        frame.style.cssText = 'width:420px;height:525px;max-width:none;border-radius:0;box-shadow:none;overflow:hidden;margin:0;';

        const viewport = document.querySelector('.carousel-viewport');
        if (!viewport) {
            throw new Error("Missing .carousel-viewport in the HTML file.");
        }
        viewport.style.cssText = 'width:420px;height:525px;aspect-ratio:unset;overflow:hidden;cursor:default;';

        document.body.style.cssText = 'padding:0;margin:0;display:block;overflow:hidden;';
    }""")
    await page.wait_for_timeout(500)

    total_slides = await page.locator(".carousel-track .slide").count()
    if total_slides == 0:
        raise RuntimeError(
            "No slides were found. Make sure your HTML uses '.carousel-track' with one or more '.slide' elements."
        )

    return total_slides


async def export_slides(html_path: Path, output_dir: Path, font_wait_ms: int) -> None:
    ensure_playwright_package()
    from playwright.async_api import async_playwright

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    output_stem = get_output_stem(html_path)
    run_number = get_next_run_number(output_dir, output_stem)
    html_content = html_path.read_text(encoding="utf-8")

    print(f"Input file: {html_path.name}")
    print("Launching browser for export...")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch()
        except Exception as exc:
            if "Executable doesn't exist" not in str(exc):
                raise
            install_chromium()
            browser = await p.chromium.launch()

        page = await browser.new_page(
            viewport={"width": VIEW_W, "height": VIEW_H},
            device_scale_factor=SCALE,
        )

        total_slides = await prepare_page(page, html_content, font_wait_ms)

        for i in range(total_slides):
            slide_number = i + 1
            await page.evaluate("""({ index, width }) => {
                const track = document.querySelector('.carousel-track');
                if (!track) {
                    throw new Error("Missing .carousel-track in the HTML file.");
                }
                track.style.transition = 'none';
                track.style.transform = 'translateX(' + (-index * width) + 'px)';
            }""", {"index": i, "width": VIEW_W})
            await page.wait_for_timeout(400)

            output_path = build_output_path(output_dir, output_stem, run_number, slide_number)
            await page.screenshot(
                path=str(output_path),
                clip={"x": 0, "y": 0, "width": VIEW_W, "height": VIEW_H},
            )
            print(f"Exported Slide {slide_number}/{total_slides}: {output_path.name}")

        await browser.close()

    print(f"Export complete!\nFolder: {output_dir.name}")
    print(f"Path: {output_dir.as_uri()}\n")


def main() -> None:
    args = parse_args()
    html_path = resolve_input_html(args.html)
    output_dir = Path(args.output_dir)
    asyncio.run(export_slides(html_path, output_dir, args.font_wait_ms))


if __name__ == "__main__":
    main()
