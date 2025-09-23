# list_bing_connection_id.py
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]


def main():
    cred = DefaultAzureCredential()
    client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=cred)

    with client:
        # List all project connections
        # SDK returns objects with fields like: id, name, kind, type, properties (varies by connection)
        conns = list(client.connections.list_connections())

    if not conns:
        print("No connections found in this Project.")
        return

    # Try to identify the Bing Grounding connection.
    # Depending on API shape, 'kind' or 'type' may carry the Bing.Grounding marker.
    bing_candidates = []
    for c in conns:
        # Safely read attributes for different SDK builds
        cid = getattr(c, "id", None) or getattr(c, "connection_id", None)
        name = getattr(c, "name", "")
        kind = getattr(c, "kind", "")
        ctype = getattr(c, "type", "")

        # Heuristics that usually match Bing grounding connections
        text_blob = " ".join(str(x).lower() for x in (name, kind, ctype) if x)
        if "bing" in text_blob and (
            "grounding" in text_blob or "bing.grounding" in text_blob
        ):
            bing_candidates.append((name, cid, kind or ctype))

    if not bing_candidates:
        print(
            "No Bing Grounding connection found. Check the Project > Connected resources in the portal."
        )
        print("Connections discovered:")
        for c in conns:
            print(
                f" - {getattr(c, 'name', '<no-name>')} | kind={getattr(c, 'kind', '')} | type={getattr(c, 'type', '')} | id={getattr(c, 'id', '')}"
            )
        return

    # If multiple, print all and highlight the first for convenience
    print("Bing Grounding connections:")
    for name, cid, meta in bing_candidates:
        print(f" - name={name} | id={cid} | meta={meta}")

    # Convenience: exportable line for your env (pick the first)
    first = bing_candidates[0]
    if first[1]:
        print("\n# To use in your shell:")
        print(f'export BING_CONNECTION_ID="{first[1]}"')


if __name__ == "__main__":
    main()
