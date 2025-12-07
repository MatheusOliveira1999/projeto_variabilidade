from __future__ import annotations

import argparse
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

DEFAULT_VARIABLE = "near_surface_air_temperature"
DEFAULT_EXPERIMENTS = ["ssp1_2_6", "ssp5_8_5"]
BASE_DIR = Path("date")
OUTPUT_DIR = Path("img")
ALIASES = {
    "near_surface_air_temperature": ["tas", "t2m"],
    "near_surface_wind_speed": ["sfcWind", "wind_speed", "wind"],
    "total_precipitation": ["tp", "pr", "precipitation"],
}
TEMP_NAMES = {"near_surface_air_temperature", "tas", "t2m"}
WIND_SPEED_NAMES = {"near_surface_wind_speed", "sfcWind", "wind_speed", "wind"}
WIND_U_ALIASES = ["uas", "u10", "eastward_wind", "eastward_near_surface_wind"]
WIND_V_ALIASES = ["vas", "v10", "northward_wind", "northward_near_surface_wind"]
COLORS = {
    "historical": "gray",
    "ssp1_2_6": "green",
    "ssp5_8_5": "orange",
}
AGG_METHODS = {
    # Para variáveis acumulativas, use soma; demais, média.
    "total_precipitation": "sum",
    "tp": "sum",
    "pr": "sum",
    "precipitation": "sum",
}


@contextmanager
def open_dataset_maybe_zip(path: Path):
    """
    Abre um arquivo NetCDF diretamente ou dentro de um .zip.
    Garante limpeza do temporário ao sair do contexto.
    """
    if path.suffix.lower() == ".zip":
        import zipfile

        with tempfile.TemporaryDirectory() as td:
            with zipfile.ZipFile(path, "r") as zf:
                members = [m for m in zf.namelist() if m.endswith(".nc")]
                if not members:
                    raise FileNotFoundError(f"Nenhum .nc dentro do zip: {path}")
                member = members[0]
                zf.extract(member, td)
            nc_path = Path(td) / member
            ds = xr.open_dataset(nc_path)
            try:
                yield ds
            finally:
                ds.close()
            return

    ds = xr.open_dataset(path)
    try:
        yield ds
    finally:
        ds.close()


def find_file(base: Path, experiment: str, variable: str) -> Optional[Path]:
    subdir = "historico" if experiment == "historical" else "projecao"
    folder = base / subdir
    if not folder.exists():
        return None

    patterns = [
        f"*{experiment}*{variable}*.nc",
        f"*{variable}*{experiment}*.nc",
        f"*{experiment}*{variable}*.zip",
        f"*{variable}*{experiment}*.zip",
    ]

    candidates: List[Path] = []
    for pattern in patterns:
        candidates.extend(folder.glob(pattern))
    if not candidates:
        return None

    # Escolhe o mais recente pela data de modificação.
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def guess_lat_lon_dims(da: xr.DataArray) -> List[str]:
    dims = []
    for name in ("latitude", "lat"):
        if name in da.dims:
            dims.append(name)
            break
    for name in ("longitude", "lon"):
        if name in da.dims:
            dims.append(name)
            break
    return dims


def spatial_mean(da: xr.DataArray) -> xr.DataArray:
    dims = guess_lat_lon_dims(da)
    return da.mean(dim=dims) if dims else da


def annual_mean(da: xr.DataArray) -> xr.DataArray:
    # 'Y' está depreciado; usar 'YE' (year-end) para ficar alinhado ao pandas.
    return da.resample(time="YE").mean("time")


def annual_sum(da: xr.DataArray) -> xr.DataArray:
    return da.resample(time="YE").sum("time")


def get_agg_method(variable: str) -> str:
    return AGG_METHODS.get(variable, "mean")


def monthly_aggregate(da: xr.DataArray, method: str) -> xr.DataArray:
    if method == "sum":
        return da.resample(time="1MS").sum("time")
    return da.resample(time="1MS").mean("time")


def monthly_climatology(da: xr.DataArray, method: str) -> xr.DataArray:
    monthly = monthly_aggregate(da, method)
    return monthly.groupby("time.month").mean("time")


def annual_aggregate(da: xr.DataArray, method: str) -> xr.DataArray:
    if method == "sum":
        return annual_sum(da)
    return annual_mean(da)


def format_label(variable: str, units: Optional[str]) -> str:
    if units:
        return f"{variable} ({units})"
    return variable


def plot_monthly_climatology(clims: Dict[str, xr.DataArray], title_var: str, y_label: str, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    months = np.arange(1, 13)
    for label, data in clims.items():
        series = data.to_pandas()
        color = COLORS.get(label)
        ax.plot(months, series.values, marker="o", label=label, color=color)
    ax.set_xlabel("Mês")
    ax.set_ylabel(y_label)
    ax.set_title(f"Climatologia mensal - {title_var}")
    ax.set_xticks(months)
    ax.legend()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)


def plot_annual_series(series: Dict[str, xr.DataArray], means: Dict[str, float], title_var: str, y_label: str, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, data in series.items():
        s = data.to_pandas()
        color = COLORS.get(label)
        ax.plot(s.index.year, s.values, marker="o", label=label, color=color)
    # Linhas horizontais das médias (histórica e cenários)
    for name, mean_val in means.items():
        color = COLORS.get(name)
        ax.axhline(mean_val, color=color, linestyle="--", linewidth=1, label=f"Média {name}")
    ax.set_xlabel("Ano")
    ax.set_ylabel(y_label)
    ax.set_title(f"Série anual - {title_var}")
    ax.legend()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)


def plot_monthly_anomalies(anoms: Dict[str, xr.DataArray], title_var: str, y_label: str, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    months = np.arange(1, 13)
    for label, data in anoms.items():
        s = data.to_pandas()
        color = COLORS.get(label)
        ax.plot(months, s.values, marker="o", label=label, color=color)
    ax.axhline(0, color="gray", linewidth=1)
    ax.set_xlabel("Mês")
    ax.set_ylabel(y_label)
    ax.set_title(f"Anomalia mensal vs. histórico - {title_var}")
    ax.set_xticks(months)
    ax.legend()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)


def plot_annual_anomalies(anoms: Dict[str, xr.DataArray], title_var: str, y_label: str, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, data in anoms.items():
        s = data.to_pandas()
        color = COLORS.get(label)
        ax.plot(s.index.year, s.values, marker="o", label=label, color=color)
    ax.axhline(0, color="gray", linewidth=1, linestyle="--")
    ax.set_xlabel("Ano")
    ax.set_ylabel(y_label)
    ax.set_title(f"Anomalia anual vs. média histórica - {title_var}")
    ax.legend()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)


def load_wind_direction(path: Path) -> Optional[xr.DataArray]:
    with open_dataset_maybe_zip(path) as ds:
        u_name = next((n for n in WIND_U_ALIASES if n in ds), None)
        v_name = next((n for n in WIND_V_ALIASES if n in ds), None)
        if not u_name or not v_name:
            return None
        u = spatial_mean(ds[u_name]).sortby("time").load()
        v = spatial_mean(ds[v_name]).sortby("time").load()
        direction = (np.degrees(np.arctan2(-u, -v)) + 360) % 360  # direção de onde o vento sopra
        direction.name = "wind_direction"
        direction.attrs["units"] = "degrees_from_north"
        return direction


def plot_wind_rose(directions: Dict[str, xr.DataArray], output: Path) -> None:
    valid = {k: v for k, v in directions.items() if v is not None}
    if not valid:
        print("[aviso] Rosa dos ventos ignorada: componentes de vento (u/v) não encontrados.")
        return
    n = len(valid)
    fig, axes = plt.subplots(1, n, subplot_kw={"projection": "polar"}, figsize=(4 * n, 4))
    if n == 1:
        axes = [axes]
    bins = np.deg2rad(np.linspace(0, 360, 17))
    for ax, (label, direction) in zip(axes, valid.items()):
        angles = np.deg2rad(direction.values)
        angles = angles[~np.isnan(angles)]
        if angles.size == 0:
            continue
        counts, _ = np.histogram(angles, bins=bins)
        freq = counts / counts.sum() * 100.0
        ax.bar(bins[:-1], freq, width=np.diff(bins), align="edge", color=COLORS.get(label), edgecolor="k", alpha=0.7)
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)  # sentido horário
        ax.set_title(f"Rosa dos ventos - {label}")
        ax.set_yticklabels([])
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)


def compute_return_levels(data: xr.DataArray, periods: List[int]) -> Dict[int, float]:
    try:
        from scipy.stats import genextreme
    except ImportError as exc:
        raise ImportError("scipy é necessário para cálculo de período de retorno.") from exc

    values = data.values
    values = values[np.isfinite(values)]
    if values.size < 5:
        raise ValueError("Série muito curta para estimar extremos.")
    shape, loc, scale = genextreme.fit(values)
    levels = {p: float(genextreme.ppf(1 - 1 / p, shape, loc=loc, scale=scale)) for p in periods}
    return levels


def plot_return_levels(levels: Dict[str, Dict[int, float]], periods: List[int], title_var: str, y_label: str, output: Path) -> None:
    if not levels:
        print("[aviso] Nenhum nível de retorno calculado.")
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    periods_sorted = sorted(periods)
    for label, lvls in levels.items():
        y = [lvls[p] for p in periods_sorted if p in lvls]
        x = [p for p in periods_sorted if p in lvls]
        color = COLORS.get(label)
        ax.plot(x, y, marker="o", label=label, color=color)
    ax.set_xlabel("Período de retorno (anos)")
    ax.set_ylabel(y_label)
    ax.set_title(f"Níveis de retorno - {title_var}")
    ax.legend()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)


def parse_scenario_files(pairs: Iterable[str]) -> Dict[str, Path]:
    mapping: Dict[str, Path] = {}
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"Formato inválido em --scenario-file: {item}. Use experimento=arquivo.nc")
        name, path = item.split("=", 1)
        mapping[name.strip()] = Path(path.strip())
    return mapping


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera gráficos de climatologia e anomalia a partir de NetCDF baixados."
    )
    parser.add_argument("--variable", default=DEFAULT_VARIABLE, help="Variável a analisar.")
    parser.add_argument(
        "--experiments",
        nargs="+",
        default=DEFAULT_EXPERIMENTS,
        help="Experimentos de projeção a comparar (além do histórico).",
    )
    parser.add_argument(
        "--historical-file",
        type=Path,
        help="Arquivo NetCDF/zip do histórico. Se ausente, tenta encontrar em date/historico.",
    )
    parser.add_argument(
        "--scenario-file",
        action="append",
        default=[],
        help="Mapeia experimento para arquivo: ssp1_2_6=caminho.nc (pode repetir).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=BASE_DIR,
        help="Diretório base onde ficam historico/ e projecao/ (padrão: date).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Diretório para salvar gráficos.",
    )
    parser.add_argument(
        "--return-periods",
        nargs="+",
        type=int,
        default=[10, 20, 50],
        help="Períodos de retorno (anos) para extremos de vento.",
    )
    return parser.parse_args()


def load_series(path: Path, variable: str) -> xr.DataArray:
    with open_dataset_maybe_zip(path) as ds:
        target_var = variable
        if target_var not in ds:
            # Tenta aliases comuns (ex.: near_surface_air_temperature -> tas)
            for alias in ALIASES.get(variable, []):
                if alias in ds:
                    target_var = alias
                    break
        if target_var not in ds:
            # Se há apenas uma variável de dados, use-a.
            data_vars = list(ds.data_vars)
            if len(data_vars) == 1:
                target_var = data_vars[0]
            else:
                raise KeyError(
                    f"Variável {variable} não encontrada em {path.name}. Disponíveis: {', '.join(data_vars)}"
                )

        da = spatial_mean(ds[target_var])
        # Converte temperatura de K para °C quando aplicável.
        if variable in TEMP_NAMES or target_var in TEMP_NAMES:
            units = str(da.attrs.get("units", "")).lower()
            if "k" in units or units in {"kelvin", "k"}:
                da = da - 273.15
                da.attrs["units"] = "degC"
        da = da.sortby("time").load()  # carrega em memória para independência do arquivo
        return da


def main() -> None:
    args = parse_args()
    scenario_map = parse_scenario_files(args.scenario_file) if args.scenario_file else {}

    hist_path = args.historical_file or find_file(args.data_dir, "historical", args.variable)
    if hist_path is None:
        raise FileNotFoundError("Arquivo histórico não encontrado. Use --historical-file ou baixe em date/historico.")

    hist_series = load_series(hist_path, args.variable)
    units = str(hist_series.attrs.get("units", "")).strip() or None
    y_label = format_label(args.variable, units)
    agg_method = get_agg_method(args.variable)

    hist_clim = monthly_climatology(hist_series, agg_method)
    hist_annual = annual_aggregate(hist_series, agg_method)

    scenario_series: Dict[str, xr.DataArray] = {}
    for experiment in args.experiments:
        path = scenario_map.get(experiment) or find_file(args.data_dir, experiment, args.variable)
        if path is None:
            print(f"[aviso] Arquivo não encontrado para {experiment}. Pulei.")
            continue
        scenario_series[experiment] = load_series(path, args.variable)

    if not scenario_series:
        raise FileNotFoundError("Nenhum arquivo de cenário encontrado.")

    scenario_clims = {k: monthly_climatology(v, agg_method) for k, v in scenario_series.items()}
    monthly_anoms = {k: clim - hist_clim for k, clim in scenario_clims.items()}
    scenario_annual = {k: annual_aggregate(v, agg_method) for k, v in scenario_series.items()}
    annual_series = {"historical": hist_annual, **scenario_annual}
    annual_means = {name: float(arr.mean().values) for name, arr in annual_series.items()}

    # Anomalia anual (cenários vs média histórica, não acumulada)
    hist_mean_scalar = annual_means["historical"]
    annual_anoms = {name: (arr - hist_mean_scalar) for name, arr in scenario_annual.items()}

    # Rosa dos ventos (se dados de direção estiverem disponíveis)
    wind_dirs: Dict[str, Optional[xr.DataArray]] = {}
    if args.variable in WIND_SPEED_NAMES:
        wind_dirs["historical"] = load_wind_direction(hist_path)
        for experiment in scenario_series.keys():
            path = scenario_map.get(experiment) or find_file(args.data_dir, experiment, args.variable)
            wind_dirs[experiment] = load_wind_direction(path) if path else None

    # Extremos de vento: níveis de retorno
    return_levels: Dict[str, Dict[int, float]] = {}
    if args.variable in WIND_SPEED_NAMES:
        try:
            hist_max = annual_max(hist_series)
            return_levels["historical"] = compute_return_levels(hist_max, args.return_periods)
            for name, series in scenario_series.items():
                scen_max = annual_max(series)
                return_levels[name] = compute_return_levels(scen_max, args.return_periods)
        except Exception as exc:  # captura erros de ajuste ou série curta
            print(f"[aviso] Não foi possível calcular níveis de retorno: {exc}")

    output_dir = args.output_dir
    plot_monthly_climatology({"historical": hist_clim, **scenario_clims}, args.variable, y_label, output_dir / f"{args.variable}_climatologia_mensal.png")
    plot_annual_series(annual_series, annual_means, args.variable, y_label, output_dir / f"{args.variable}_serie_anual.png")
    plot_monthly_anomalies(monthly_anoms, args.variable, f"Anomalia de {y_label}", output_dir / f"{args.variable}_anomalias_mensais.png")
    plot_annual_anomalies(annual_anoms, args.variable, f"Anomalia anual de {y_label}", output_dir / f"{args.variable}_anomalias_anuais.png")
    if args.variable in WIND_SPEED_NAMES:
        plot_wind_rose(wind_dirs, output_dir / f"{args.variable}_rosa_dos_ventos.png")
        plot_return_levels(return_levels, args.return_periods, args.variable, y_label, output_dir / f"{args.variable}_niveis_retorno.png")

    print(f"[ok] Gráficos salvos em {output_dir}")


if __name__ == "__main__":
    main()
