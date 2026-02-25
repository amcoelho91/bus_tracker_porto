def parse_annotations(values: list[str] | None) -> dict[str, str]:
    """
    Convert ["stcp:route:504", "stcp:sentido:1"] into {"stcp:route":"504", "stcp:sentido":"1"}.
    """
    out: dict[str, str] = {}
    for s in values or []:
        parts = s.split(":", 2)
        if len(parts) == 3:
            out[f"{parts[0]}:{parts[1]}"] = parts[2]
    return out

def get_value(entity: dict, key: str, default=None):
    obj = entity.get(key)
    if isinstance(obj, dict):
        return obj.get("value", default)
    return default

def extract_lon_lat(entity: dict) -> tuple[float, float]:
    # entity["location"]["value"]["coordinates"] = [lon, lat]
    coords = entity["location"]["value"]["coordinates"]
    return float(coords[0]), float(coords[1])