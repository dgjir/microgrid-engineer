#!/usr/bin/env python3
"""
Microgrid Engineer MCP Server
Provides calculation tools for microgrid design and simulation.
Uses raw JSON-RPC 2.0 over stdio (no external MCP SDK required).
"""

import sys
import json
import math
import numpy as np

# MCP Protocol implementation
def write_msg(msg):
    """Write a JSON-RPC message over stdio."""
    data = json.dumps(msg, ensure_ascii=False)
    sys.stdout.write(f"Content-Length: {len(data)}\r\n\r\n{data}")
    sys.stdout.flush()

def read_msg():
    """Read a JSON-RPC message from stdio."""
    line = sys.stdin.readline()
    while line.strip() == "":
        line = sys.stdin.readline()
    if not line.startswith("Content-Length:"):
        return None
    length = int(line.strip().split(":")[1].strip())
    _ = sys.stdin.readline()  # blank line
    data = sys.stdin.read(length)
    return json.loads(data)

# --- Tool Implementations ---

def cable_sizing(params):
    """Calculate cable cross-section based on current, length, and voltage drop requirements."""
    I = params.get("current_a", 100)
    length_m = params.get("length_m", 100)
    voltage_v = params.get("voltage_v", 400) 
    max_drop_percent = params.get("max_drop_percent", 3)
    cable_type = params.get("cable_type", "cu")  # cu or al
    ac = params.get("ac", True)
    power_factor = params.get("power_factor", 0.95)
    
    # Resistivity (ohm-mm²/m)
    rho = 0.0172 if cable_type == "cu" else 0.0282
    
    if ac:
        # For AC: S = sqrt(3) * rho * 2L * I * cosφ / ΔV
        delta_v = voltage_v * max_drop_percent / 100
        s_min = math.sqrt(3) * rho * 2 * length_m * I * power_factor / delta_v
    else:
        # For DC: S = 2 * rho * L * I / ΔV
        delta_v = voltage_v * max_drop_percent / 100
        s_min = 2 * rho * length_m * I / delta_v
    
    # Standard sizes (mm²)
    std_sizes = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400, 500]
    
    selected = next((s for s in std_sizes if s >= s_min), 500)
    if selected >= 500 and s_min > 500:
        selected = math.ceil(s_min / 10) * 10
    
    # Ampacity lookup (approximate, pvc insulated, 30°C ambient)
    ampacity_table = {
        "cu": {1.5: 18, 2.5: 25, 4: 34, 6: 43, 10: 60, 16: 80, 25: 107, 35: 130,
               50: 157, 70: 200, 95: 245, 120: 285, 150: 330, 185: 380, 240: 450},
        "al": {2.5: 20, 4: 27, 6: 35, 10: 49, 16: 65, 25: 85, 35: 105, 50: 125,
               70: 160, 95: 195, 120: 225, 150: 260, 185: 300, 240: 355}
    }
    
    ampacity = ampacity_table.get(cable_type, ampacity_table["cu"]).get(selected, "N/A")
    ampacity_ok = True if ampacity == "N/A" else (ampacity >= I * 1.25)
    
    return {
        "selected_size_mm2": selected,
        "min_size_mm2": round(s_min, 1),
        "type": cable_type.upper(),
        "voltage_drop_percent": round(max_drop_percent, 1),
        "actual_vd_percent": round(delta_v / voltage_v * 100, 2),
        "ampacity_a": ampacity,
        "ampacity_ok": ampacity_ok,
        "degradation_factor_30c": 1.0,
        "recommendation": f"Use {selected}mm² {cable_type.upper()} cable" + (" (ampacity OK)" if ampacity_ok else " (CHECK AMPACITY)")
    }


def battery_sizing(params):
    """Calculate battery capacity for microgrid energy storage."""
    load_kwh = params.get("load_kwh_per_day", 100)
    backup_hours = params.get("backup_hours", 4)
    dod = params.get("depth_of_discharge", 0.8)
    rte = params.get("round_trip_efficiency", 0.92)
    dc_voltage = params.get("dc_voltage_v", 400)
    autonomy_days = params.get("autonomy_days", 1)
    cell_v = params.get("cell_voltage_v", 3.2)  # LFP nominal
    cell_ah = params.get("cell_capacity_ah", 280)  # LFP typical
    
    avg_power_kw = load_kwh / 24
    required_energy_kwh = avg_power_kw * backup_hours * autonomy_days / (dod * rte)
    required_energy_kj = required_energy_kwh * 3600
    
    # Cell level
    cell_energy_kwh = cell_v * cell_ah / 1000
    cells_needed = math.ceil(required_energy_kwh / cell_energy_kwh)
    
    # Series/parallel configuration
    cells_per_string = math.ceil(dc_voltage / cell_v)
    strings_parallel = math.ceil(cells_needed / cells_per_string)
    total_cells = cells_per_string * strings_parallel
    actual_energy_kwh = total_cells * cell_energy_kwh * dod * rte
    
    return {
        "required_energy_kwh": round(required_energy_kwh, 1),
        "avg_load_power_kw": round(avg_power_kw, 1),
        "backup_hours": backup_hours,
        "dod": dod,
        "rte": rte,
        "battery_config": {
            "cells_per_string": cells_per_string,
            "strings_parallel": strings_parallel,
            "total_cells": total_cells,
            "nominal_voltage_v": cells_per_string * cell_v,
            "dc_voltage_v": dc_voltage
        },
        "actual_deliverable_kwh": round(actual_energy_kwh, 1),
        "cell_type": f"LFP {cell_ah}Ah/{cell_v}V",
        "recommendation": f"Configure {cells_per_string}S{strings_parallel}P ({total_cells} cells, {round(cells_per_string * cell_v, 1)}V nominal)"
    }


def pv_yield(params):
    """Estimate annual PV energy yield."""
    peak_kw = params.get("peak_kw", 100)
    ghi_kwh_m2 = params.get("annual_ghi_kwh_m2", 1500)
    tilt = params.get("tilt_deg", 25)
    azimuth = params.get("azimuth_deg", 180)
    derating = params.get("derating_factor", 0.80)
    
    # Simple tilt/azimuth correction factor (approximate)
    latitude_correction = 1.0 + 0.1 * abs(tilt - abs(latitude := params.get("latitude_deg", 30))) / 30
    azimuth_correction = 1.0 - 0.05 * abs(azimuth - 180) / 180 if azimuth < 270 and azimuth > 90 else 0.7
    
    effective_sun = ghi_kwh_m2 * latitude_correction * azimuth_correction
    annual_mwh = peak_kw * effective_sun * derating / 1000
    
    # Monthly breakdown (simplified sine distribution for northern hemisphere)
    base = np.array([0.35, 0.40, 0.55, 0.65, 0.75, 0.80, 0.82, 0.78, 0.68, 0.55, 0.42, 0.33])
    monthly_mwh = base * annual_mwh / base.sum()
    
    return {
        "annual_yield_mwh": round(annual_mwh, 1),
        "capacity_factor_percent": round(annual_mwh / (peak_kw * 8.76), 1),
        "effective_sun_hours": round(effective_sun, 1),
        "derating_factor": derating,
        "monthly_mwh": [round(m, 1) for m in monthly_mwh],
        "tilt_correction": round(latitude_correction, 3),
        "azimuth_correction": round(azimuth_correction, 3),
        "recommendation": f"Expected annual yield: {round(annual_mwh, 1)} MWh (CF: {round(annual_mwh / (peak_kw * 8.76), 1)}%)"
    }


def transformer_sizing(params):
    """Calculate transformer size for microgrid interconnection."""
    apparent_power_kva = params.get("total_apparent_power_kva", 500)
    future_margin = params.get("future_margin_percent", 20)
    ambient_temp_c = params.get("ambient_temp_c", 35)
    altitude_m = params.get("altitude_m", 500)
    oil_type = params.get("oil_type", "mineral")  # mineral, silicone, ester
    cooling = params.get("cooling_type", "ONAN")
    
    # Derating factors
    temp_factor = 1.0 - max(0, (ambient_temp_c - 30)) * 0.008
    alt_factor = 1.0 - altitude_m * 0.003 / 500
    total_derating = temp_factor * alt_factor
    
    rated_kva = math.ceil(apparent_power_kva * (1 + future_margin / 100) / total_derating / 50) * 50
    
    # Typical impedance
    z_percent = 5.0 if rated_kva <= 1000 else 6.5 if rated_kva <= 5000 else 8.0
    
    return {
        "recommended_kva": rated_kva,
        "current_load_kva": apparent_power_kva,
        "margin_kva": rated_kva - apparent_power_kva / total_derating,
        "derating_factors": {
            "temperature": round(temp_factor, 3),
            "altitude": round(alt_factor, 3),
            "total": round(total_derating, 3)
        },
        "impedance_percent": z_percent,
        "oil_type": oil_type,
        "cooling": cooling,
        "standard": "IEC 60076",
        "recommendation": f"Select {rated_kva}kVA {oil_type}-oil transformer, Z={z_percent}%, {cooling}"
    }


def microgrid_planning(params):
    """Run a microgrid planning study with basic constraints."""
    pv_kw = params.get("pv_kw", 500)
    wind_kw = params.get("wind_kw", 0)
    bess_kwh = params.get("bess_kwh", 1000)
    bess_kw = params.get("bess_kw", 250)
    diesel_kw = params.get("diesel_kw", 200)
    peak_load_kw = params.get("peak_load_kw", 400)
    avg_load_kw = params.get("avg_load_kw", 250)
    cf_pv = params.get("pv_capacity_factor", 0.18)
    cf_wind = params.get("wind_capacity_factor", 0.28)
    diesel_cost = params.get("diesel_fuel_cost_per_liter", 7.5)
    grid_cost = params.get("grid_energy_cost_per_kwh", 0.80) if params.get("grid_connected", False) else None
    
    # Energy estimates (annual)
    pv_mwh_year = pv_kw * cf_pv * 8760 / 1000
    wind_mwh_year = wind_kw * cf_wind * 8760 / 1000
    load_mwh_year = avg_load_kw * 8760 / 1000
    
    # Renewable fraction
    ren_mwh = pv_mwh_year + wind_mwh_year
    ren_fraction = min(1.0, ren_mwh / load_mwh_year) if load_mwh_year > 0 else 0
    
    # Diesel consumption (simplified)
    diesel_needed_kwh = max(0, load_mwh_year * 1000 - ren_mwh * 1000 - bess_kwh * 365)
    diesel_liters = diesel_needed_kwh / 3.5  # 1L diesel ≈ 3.5 kWh thermal → ~1 kWh electric at 30% eff
    diesel_liters_dep = diesel_liters / 0.30  # electrical efficiency adjustment
    diesel_cost_year = diesel_liters_dep * diesel_cost
    
    # BESS cycling estimate
    bess_cycles_year = min(365, diesel_needed_kwh / bess_kwh) if bess_kwh > 0 else 0
    
    # Levelized cost of energy (simplified)
    capex = (pv_kw * 6000 + wind_kw * 12000 + bess_kwh * 3000 + bess_kw * 2000 + diesel_kw * 2500)
    opex_year = capex * 0.02 + diesel_cost_year
    lifetime = 20
    lcoe = (capex / lifetime + opex_year) / (load_mwh_year * 1000) * 100  # 元/kWh
    
    return {
    "energy_balance": {
            "pv_mwh_year": round(pv_mwh_year, 0),
            "wind_mwh_year": round(wind_mwh_year, 0),
            "renewable_mwh_year": round(ren_mwh, 0),
            "load_mwh_year": round(load_mwh_year, 0),
            "renewable_fraction": round(ren_fraction, 3),
            "diesel_fuel_liters_year": round(diesel_liters_dep, 0),
            "bess_expected_cycles_year": round(bess_cycles_year, 0)
        },
        "economic_analysis": {
            "estimated_capex_cny": round(capex, 0),
            "estimated_opex_year_cny": round(opex_year, 0),
            "diesel_cost_year_cny": round(diesel_cost_year, 0),
            "lcoe_cny_per_kwh": round(lcoe, 3)
        },
        "system_metrics": {
            "re_peak_ratio": round((pv_kw + wind_kw) / peak_load_kw, 2),
            "storage_duration_hours": round(bess_kwh / bess_kw, 1) if bess_kw > 0 else 0,
            "diesel_backup_percent": round(diesel_kw / peak_load_kw * 100, 0) if peak_load_kw > 0 else 0
        },
        "recommendation": f"RE fraction: {round(ren_fraction*100, 0)}% | LCOE: {round(lcoe, 2)} 元/kWh"
    }


# --- Tool Registration ---
TOOLS = {
    "microgrid-cable-sizing": {
        "description": "Calculate cable cross-section for AC/DC microgrid based on current, length, voltage drop",
        "params": {
            "current_a": "Load current in amperes",
            "length_m": "Cable length in meters",
            "voltage_v": "System voltage (V)",
            "max_drop_percent": "Maximum allowable voltage drop %",
            "cable_type": "cu or al (copper or aluminum)",
            "ac": "True for AC, False for DC",
            "power_factor": "Power factor (default 0.95)"
        },
        "handler": cable_sizing
    },
    "microgrid-battery-sizing": {
        "description": "Calculate BESS capacity and configuration for microgrid",
        "params": {
            "load_kwh_per_day": "Daily load energy (kWh)",
            "backup_hours": "Required backup duration (hours)",
            "depth_of_discharge": "Battery DOD (0-1)",
            "round_trip_efficiency": "Battery RTE (0-1)",
            "dc_voltage_v": "DC bus voltage (V)",
            "autonomy_days": "Days of autonomy",
            "cell_voltage_v": "Cell nominal voltage (V)",
            "cell_capacity_ah": "Cell capacity (Ah)"
        },
        "handler": battery_sizing
    },
    "microgrid-pv-yield": {
        "description": "Estimate annual PV energy yield for a given location and system size",
        "params": {
            "peak_kw": "PV peak power (kWp)",
            "annual_ghi_kwh_m2": "Annual GHI (kWh/m²)",
            "tilt_deg": "Panel tilt angle (degrees)",
            "azimuth_deg": "Panel azimuth (degrees, 180=south)",
            "derating_factor": "System derating factor (0-1)",
            "latitude_deg": "Site latitude"
        },
        "handler": pv_yield
    },
    "microgrid-transformer-sizing": {
        "description": "Calculate transformer rating for microgrid interconnection",
        "params": {
            "total_apparent_power_kva": "Total connected apparent power (kVA)",
            "future_margin_percent": "Future expansion margin (%)",
            "ambient_temp_c": "Ambient temperature (°C)",
            "altitude_m": "Site altitude (m)",
            "oil_type": "mineral, silicone, or ester",
            "cooling_type": "ONAN, ONAF, OFAF"
        },
        "handler": transformer_sizing
    },
    "microgrid-planning-study": {
        "description": "Run a basic microgrid planning study with sizing, energy balance, and economics",
        "params": {
            "pv_kw": "PV system size (kWp)",
            "wind_kw": "Wind turbine size (kW)",
            "bess_kwh": "Battery capacity (kWh)",
            "bess_kw": "Battery power rating (kW)",
            "diesel_kw": "Diesel genset size (kW)",
            "peak_load_kw": "Peak load (kW)",
            "avg_load_kw": "Average load (kW)",
            "pv_capacity_factor": "PV capacity factor (0-1)",
            "wind_capacity_factor": "Wind capacity factor (0-1)",
            "diesel_fuel_cost_per_liter": "Diesel cost per liter (CNY)",
            "grid_connected": "Whether grid connection exists"
        },
        "handler": microgrid_planning
    }
}

# --- Main Loop ---
def main():
    # Send initialize response
    write_msg({
        "jsonrpc": "2.0",
        "id": "init",
        "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "microgrid-engineer",
                "version": "0.1.0"
            },
            "capabilities": {
                "tools": {}
            }
        }
    })
    
    while True:
        msg = read_msg()
        if msg is None:
            break
        
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params", {})
        
        try:
            if method == "tools/list":
                tools_list = [{
                    "name": name,
                    "description": info["description"],
                    "inputSchema": {
                        "type": "object",
                        "properties": {k: {"type": "number", "description": v} if k in ["current_a", "length_m", "voltage_v", "max_drop_percent", "power_factor", "load_kwh_per_day", "backup_hours", "depth_of_discharge", "round_trip_efficiency", "dc_voltage_v", "autonomy_days", "cell_voltage_v", "cell_capacity_ah", "peak_kw", "annual_ghi_kwh_m2", "tilt_deg", "azimuth_deg", "derating_factor", "latitude_deg", "total_apparent_power_kva", "future_margin_percent", "ambient_temp_c", "altitude_m", "pv_kw", "wind_kw", "bess_kwh", "bess_kw", "diesel_kw", "peak_load_kw", "avg_load_kw", "pv_capacity_factor", "wind_capacity_factor", "diesel_fuel_cost_per_liter", "grid_energy_cost_per_kwh"] else {"type": "string", "description": v} for k, v in info["params"].items()},
                        "required": list(info["params"].keys())
                    }
                } for name, info in TOOLS.items()]
                
                write_msg({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools_list}})
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name in TOOLS:
                    result = TOOLS[tool_name]["handler"](arguments)
                    write_msg({"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}]}})
                else:
                    write_msg({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}})
            
            else:
                write_msg({"jsonrpc": "2.0", "id": msg_id, "result": {}})
                
        except Exception as e:
            write_msg({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": str(e)}})

if __name__ == "__main__":
    main()
