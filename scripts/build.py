#!/usr/bin/env python3
"""Build index.html from template.html with the repo list baked in.

Usage:
  python3 scripts/build.py                  # fetch from GitHub (needs GH_TOKEN + gh CLI)
  python3 scripts/build.py response.json    # use a saved GraphQL response (local testing)
"""
import json
import pathlib
import subprocess
import sys

OWNER = "efthymios-ks"
TARGET_LISTS = {
    "net": ".NET",
    "powershell": "PowerShell",
    "extensions": "Extensions",
    "web-apps": "Web Apps",
}

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "template.html"
OUTPUT = ROOT / "index.html"
PLACEHOLDER = "__PORTFOLIO_PAYLOAD__"

QUERY = """
query($login: String!) {
  user(login: $login) {
    lists(first: 20) {
      nodes {
        slug
        items(first: 100) {
          nodes {
            ... on Repository {
              name
              description
              url
              isPrivate
              owner { login }
            }
          }
        }
      }
    }
  }
}
"""


def fetch_response() -> dict:
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"login={OWNER}"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def is_publishable(item: dict) -> bool:
    return (
        bool(item.get("name"))
        and not item.get("isPrivate")
        and (item.get("owner") or {}).get("login") == OWNER
        and bool(item.get("description"))
    )


def build_payload(response: dict) -> dict:
    repos: dict[str, dict] = {}

    for lst in response["data"]["user"]["lists"]["nodes"]:
        label = TARGET_LISTS.get(lst["slug"])
        if not label:
            continue
        for item in lst["items"]["nodes"]:
            if not item or not is_publishable(item):
                continue
            repo = repos.setdefault(item["name"], {
                "name": item["name"],
                "html_url": item["url"],
                "description": item["description"],
                "lists": [],
            })
            if label not in repo["lists"]:
                repo["lists"].append(label)

    return {"repos": sorted(repos.values(), key=lambda repo: repo["name"].casefold())}


def render(payload: dict) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        sys.exit(f"{TEMPLATE.name} must contain {PLACEHOLDER} exactly once")
    # Escape '<' so repo text can never close the <script> tag early.
    data = json.dumps(payload, ensure_ascii=False, indent=4).replace("<", "\\u003c")
    return template.replace(PLACEHOLDER, data)


def main() -> None:
    if len(sys.argv) > 1:
        response = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        response = fetch_response()

    payload = build_payload(response)
    if not payload["repos"]:
        sys.exit("No repos found; refusing to publish an empty portfolio")

    OUTPUT.write_text(render(payload), encoding="utf-8")
    print(f"Built {OUTPUT.name} with {len(payload['repos'])} repos")


if __name__ == "__main__":
    main()
