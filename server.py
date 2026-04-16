from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
import threading
from fastmcp import FastMCP
import httpx
import os
import json
from typing import Optional, List

mcp = FastMCP("globalping")

BASE_URL = "https://api.globalping.io"
API_TOKEN = os.environ.get("GLOBALPING_API_TOKEN", "")


def get_headers(token: Optional[str] = None) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    auth_token = token or API_TOKEN
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


@mcp.tool()
async def check_health() -> dict:
    """Check the health and status of the Globalping API server. Use this to verify the API is running, responsive, and all dependent services (Redis, database, etc.) are operational before making other requests."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/v1/health",
                headers=get_headers(),
                timeout=10.0,
            )
            if response.status_code == 200:
                try:
                    return {"status": "healthy", "data": response.json()}
                except Exception:
                    return {"status": "healthy", "body": response.text}
            else:
                return {
                    "status": "unhealthy",
                    "status_code": response.status_code,
                    "body": response.text,
                }
        except httpx.RequestError as e:
            return {"status": "error", "error": str(e)}


@mcp.tool()
async def run_measurement(
    type: str,
    target: str,
    locations: Optional[str] = None,
    limit: Optional[int] = 1,
    measurementOptions: Optional[str] = None,
) -> dict:
    """Run a network measurement (ping, traceroute, DNS lookup, MTR, HTTP) from probes distributed around the world. Use this when you need to test network routing, latency, DNS resolution, or HTTP response from specific locations or globally. Specify the target host and measurement type.

    Args:
        type: Type of measurement to run: 'ping', 'traceroute', 'dns', 'mtr', or 'http'
        target: The target hostname, domain, or IP address to measure against
        locations: JSON string of array of location objects specifying where to run the measurement from. Each object can include fields like continent, country, city, region, network, or asn.
        limit: Number of probes to use for the measurement (1-500)
        measurementOptions: JSON string of additional measurement-specific options. For DNS: query type, resolver. For HTTP: method, headers, path. For ping/traceroute: packets, protocol, port.
    """
    payload: dict = {
        "type": type,
        "target": target,
    }

    if limit is not None:
        payload["limit"] = limit

    if locations is not None:
        try:
            parsed_locations = json.loads(locations)
            payload["locations"] = parsed_locations
        except json.JSONDecodeError:
            return {"error": "Invalid JSON for locations parameter"}

    if measurementOptions is not None:
        try:
            parsed_options = json.loads(measurementOptions)
            payload["measurementOptions"] = parsed_options
        except json.JSONDecodeError:
            return {"error": "Invalid JSON for measurementOptions parameter"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/v1/measurements",
                headers=get_headers(),
                json=payload,
                timeout=30.0,
            )
            try:
                data = response.json()
            except Exception:
                data = {"body": response.text}
            return {
                "status_code": response.status_code,
                "data": data,
            }
        except httpx.RequestError as e:
            return {"error": str(e)}


@mcp.tool()
async def get_measurement(measurement_id: str) -> dict:
    """Retrieve the results of a previously submitted measurement by its ID. Use this to poll for results after calling run_measurement, or to retrieve stored measurement results. Results include per-probe output, latency, and routing information.

    Args:
        measurement_id: The unique ID of the measurement returned by run_measurement
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/v1/measurements/{measurement_id}",
                headers=get_headers(),
                timeout=30.0,
            )
            try:
                data = response.json()
            except Exception:
                data = {"body": response.text}
            return {
                "status_code": response.status_code,
                "data": data,
            }
        except httpx.RequestError as e:
            return {"error": str(e)}


@mcp.tool()
async def list_probes() -> dict:
    """List available probes in the Globalping network with their geographic and network attributes. Use this to discover what locations and networks are available for measurements, or to find probes in a specific region, country, ASN, or city."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/v1/probes",
                headers=get_headers(),
                timeout=30.0,
            )
            try:
                data = response.json()
            except Exception:
                data = {"body": response.text}
            return {
                "status_code": response.status_code,
                "data": data,
            }
        except httpx.RequestError as e:
            return {"error": str(e)}


@mcp.tool()
async def get_alternative_ips(ip: str) -> dict:
    """Look up alternative or anycast IP addresses for a given IP or hostname. Use this when troubleshooting anycast routing issues to identify all IPs that may serve a given endpoint from different locations.

    Args:
        ip: The IP address or hostname to look up alternative IPs for
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/v1/ips/{ip}/alternativeIps",
                headers=get_headers(),
                timeout=15.0,
            )
            try:
                data = response.json()
            except Exception:
                data = {"body": response.text}
            return {
                "status_code": response.status_code,
                "data": data,
            }
        except httpx.RequestError as e:
            return {"error": str(e)}


@mcp.tool()
async def get_adoption_code(token: Optional[str] = None) -> dict:
    """Generate or retrieve an adoption code used to register and link a probe to the Globalping network. Use this when onboarding a new probe or verifying probe ownership credentials.

    Args:
        token: Optional authentication token to associate the adoption code with a specific user account
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/v1/adoption-code",
                headers=get_headers(token=token),
                timeout=15.0,
            )
            try:
                data = response.json()
            except Exception:
                data = {"body": response.text}
            return {
                "status_code": response.status_code,
                "data": data,
            }
        except httpx.RequestError as e:
            return {"error": str(e)}


@mcp.tool()
async def geoip_lookup(ip: str) -> dict:
    """Look up geographic and network information for an IP address using the GeoIP database. Use this to determine the country, city, region, ASN, and approximate location of an IP address for filtering or analysis purposes.

    Args:
        ip: The IP address to look up geographic information for
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/v1/ips/{ip}",
                headers=get_headers(),
                timeout=15.0,
            )
            try:
                data = response.json()
            except Exception:
                data = {"body": response.text}
            return {
                "status_code": response.status_code,
                "data": data,
            }
        except httpx.RequestError as e:
            return {"error": str(e)}


@mcp.tool()
async def check_malware(target: str) -> dict:
    """Check whether an IP address or domain is flagged as malicious or associated with malware. Use this during network analysis when evaluating the trustworthiness of a target or a probe's IP before running measurements.

    Args:
        target: The IP address or domain name to check for malware or malicious activity flags
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/v1/ips/{target}/malware",
                headers=get_headers(),
                timeout=15.0,
            )
            try:
                data = response.json()
            except Exception:
                data = {"body": response.text}
            return {
                "status_code": response.status_code,
                "data": data,
            }
        except httpx.RequestError as e:
            return {"error": str(e)}




_SERVER_SLUG = "jsdelivr-globalping"

def _track(tool_name: str, ua: str = ""):
    import threading
    def _send():
        try:
            import urllib.request, json as _json
            data = _json.dumps({"slug": _SERVER_SLUG, "event": "tool_call", "tool": tool_name, "user_agent": ua}).encode()
            req = urllib.request.Request("https://www.volspan.dev/api/analytics/event", data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()

async def health(request):
    return JSONResponse({"status": "ok", "server": mcp.name})

async def tools(request):
    registered = await mcp.list_tools()
    tool_list = [{"name": t.name, "description": t.description or ""} for t in registered]
    return JSONResponse({"tools": tool_list, "count": len(tool_list)})

sse_app = mcp.http_app(transport="sse")

app = Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", sse_app),
    ],
    lifespan=sse_app.lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
