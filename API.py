from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

import cdsapi

# Ajuste aqui valores padrão que serão usados caso nenhum argumento seja passado.
DATASET = "projections-cmip6"
DEFAULT_MODEL = "ipsl_cm6a_lr"
DEFAULT_AREA = [0.25, -94.68, -23.09, -71.04]
DEFAULT_VARIABLES = [
    "near_surface_air_temperature",
    "near_surface_wind_speed",
]
DEFAULT_EXPERIMENTS = ["historical", "ssp1_2_6", "ssp5_8_5"]
HIST_RANGE = (1980, 2014)
SCENARIO_RANGE = (2015, 2049)
BASE_OUTPUT = Path("date")

MONTHS = [f"{m:02d}" for m in range(1, 13)]
DAYS = [f"{d:02d}" for d in range(1, 32)]


def year_list(start: int, end: int) -> List[str]:
    return [str(year) for year in range(start, end + 1)]


def output_dir_for_experiment(base_dir: Path, experiment: str) -> Path:
    target = base_dir / ("historico" if experiment == "historical" else "projecao")
    target.mkdir(parents=True, exist_ok=True)
    return target


def build_request(
    variable: str,
    experiment: str,
    years: Iterable[str],
    area: Iterable[float],
    model: str,
) -> dict:
    return {
        "temporal_resolution": "daily",
        "experiment": experiment,
        "variable": variable,
        "model": model,
        "year": list(years),
        "month": MONTHS,
        "day": DAYS,
        "area": list(area),
    }


def download_one(
    client: cdsapi.Client,
    variable: str,
    experiment: str,
    years: List[str],
    area: Iterable[float],
    model: str,
    target_dir: Path,
) -> Path:
    request = build_request(variable, experiment, years, area, model)
    target_file = target_dir / f"{experiment}_{variable}_{years[0]}-{years[-1]}_{model}.zip"
    client.retrieve(DATASET, request, str(target_file))
    return target_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa dados CMIP6 (histórico e projeções) via CDS API."
    )
    parser.add_argument(
        "-v",
        "--variables",
        nargs="+",
        default=DEFAULT_VARIABLES,
        help="Variáveis do CDS (ex.: near_surface_air_temperature).",
    )
    parser.add_argument(
        "-e",
        "--experiments",
        nargs="+",
        default=DEFAULT_EXPERIMENTS,
        help="Experimentos a baixar (historical, ssp1_2_6, ssp5_8_5, ...).",
    )
    parser.add_argument(
        "--area",
        nargs=4,
        type=float,
        default=DEFAULT_AREA,
        metavar=("N", "W", "S", "E"),
        help="Caixa [N W S E].",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Modelo CMIP6 (ex.: ipsl_cm6a_lr).",
    )
    parser.add_argument(
        "--historical-start",
        type=int,
        default=HIST_RANGE[0],
        help="Ano inicial do histórico.",
    )
    parser.add_argument(
        "--historical-end",
        type=int,
        default=HIST_RANGE[1],
        help="Ano final do histórico.",
    )
    parser.add_argument(
        "--scenario-start",
        type=int,
        default=SCENARIO_RANGE[0],
        help="Ano inicial dos cenários futuros.",
    )
    parser.add_argument(
        "--scenario-end",
        type=int,
        default=SCENARIO_RANGE[1],
        help="Ano final dos cenários futuros.",
    )
    parser.add_argument(
        "--output-base",
        default=str(BASE_OUTPUT),
        help="Diretório base para salvar arquivos (historico/projecao).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = cdsapi.Client()

    hist_years = year_list(args.historical_start, args.historical_end)
    scenario_years = year_list(args.scenario_start, args.scenario_end)
    base_dir = Path(args.output_base)

    for experiment in args.experiments:
        years = hist_years if experiment == "historical" else scenario_years
        target_dir = output_dir_for_experiment(base_dir, experiment)
        for variable in args.variables:
            target_file = download_one(
                client=client,
                variable=variable,
                experiment=experiment,
                years=years,
                area=args.area,
                model=args.model,
                target_dir=target_dir,
            )
            print(f"[ok] {experiment} {variable} -> {target_file}")


if __name__ == "__main__":
    main()
