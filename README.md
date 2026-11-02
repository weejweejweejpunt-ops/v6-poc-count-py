# v6-poc-count-py

A small [vantage6](https://vantage6.ai) v5 algorithm for a proof of concept: **count the rows of a dataframe per value of one
column over all participating nodes**. By default it counts persons per gender (`gender_concept_id` of the OMOP `person` table) and
labels the OMOP gender concepts (8507 = MALE, 8532 = FEMALE, ...).

Only counts leave a node, never rows. The result of the central function contains a `table`, which the vantage6 portal shows as a
table (see `ui_visualizations` in `algorithm_store.json`).

## Functions

| Function | Step type | Runs | Arguments |
|---|---|---|---|
| `central_count` | `central_compute` | on one node; creates the partial tasks and adds up | `column_name` (default `gender_concept_id`), `min_cell_size` (default `0`) |
| `partial_count` | `federated_compute` | on every node, on its own dataframe | `column_name`, `min_cell_size` |

Both take one dataframe (`@dataframe(1)`), which is created beforehand with a data-extraction algorithm such as
`ghcr.io/vantage6/algorithm/extract-basics` (`read_parquet`, `read_csv`, `read_sql_database`, ...).

Result of `central_count`:

```json
{
  "total": 2694,
  "organizations": 2,
  "table": [
    {"value": "8507", "label": "MALE", "count": 1321},
    {"value": "8532", "label": "FEMALE", "count": 1373}
  ]
}
```

### Disclosure control (basic)

`min_cell_size > 0` reports a value that occurs fewer times at a node as `null`, and a node refuses to answer if its whole dataframe has
fewer rows than that. A `null` at one node stays `null` in the total. This is a first step, **not** complete disclosure control: the
`total` is not masked, so a suppressed cell can be estimated from the other cells, and the partial results are visible to the researcher.
Agree the real rules with the data holders before using this on real data.

## Tests

```bash
uv sync
uv run pytest
```

- `tests/test_counting.py`: the counting logic (only needs pandas).
- `tests/test_store_json.py`: checks `algorithm_store.json` against the functions in the code (names, arguments, defaults, allowed types).
- `tests/test_mock_network.py`: runs central and partial in vantage6's `MockNetwork` with Parquet files and the same `read_parquet`
  function as `extract-basics` (skipped when vantage6 is not installed).

## Build and release (CI/CD, not from a laptop)

The Docker image is built by GitHub Actions. Push a tag with a version number:

```bash
git tag 0.1.0
git push origin 0.1.0
```

`.github/workflows/release.yml` calls the shared vantage6 workflow (pinned to a commit), which runs `make image` and pushes
`ghcr.io/weejweejweejpunt-ops/v6-poc-count-py:<version>-v6-<vantage6 version>`, `:latest` and `:<vantage6 major>`.

**Image format.** The algorithm store looks up the digest of an image with an `Accept` header for the plain Docker v2 manifest only
(`get_digest` in vantage6-common 5.0.3). A recent buildx pushes an OCI image index with attestations by default, which gives HTTP 404 there:
version 0.1.0 had that problem. The `Makefile` therefore builds with `--provenance=false --sbom=false`, on a `docker-container` builder, and
exports with `oci-mediatypes=false`. The last job of the release workflow (`verify-store-compatible`) checks this and fails the release otherwise.
To check it by hand:

```bash
TOKEN=$(curl -s "https://ghcr.io/token?scope=repository:weejweejweejpunt-ops/v6-poc-count-py:pull" | python -c 'import sys,json; print(json.load(sys.stdin)["token"])')
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
  https://ghcr.io/v2/weejweejweejpunt-ops/v6-poc-count-py/manifests/latest
```

`200` is good, `404` means the image cannot be used with the store.

After the first push, open the package on GitHub (Packages > `v6-poc-count-py` > Package settings) and set the visibility to **public**, otherwise
the nodes cannot pull the image without a pull secret. Also check under the repository Settings > Actions > General that workflows are allowed.

## Algorithm store

Submit `algorithm_store.json` in the algorithm store (portal: Algorithm store > add algorithm; or `client.algorithm.create()`). The store
resolves the image digest from the registry when you submit, so the store must be able to reach `ghcr.io`. A reviewer has to approve
the algorithm before it can be run from the portal.

`algorithm_store.json` is written by hand (the structure follows the official `v6-average-py`). `v6 algorithm generate-store-json` can generate it from
the docstrings and type hints; run that after changing the functions and compare the two.

## Layout

```
v6_poc_count/counting.py   counting logic, no vantage6 imports
v6_poc_count/partial.py    partial_count (federated_compute)
v6_poc_count/central.py    central_count (central_compute)
algorithm_store.json       store metadata, incl. the table visualization
Dockerfile, Makefile       image on top of ghcr.io/vantage6/infrastructure/algorithm-base:5.0
.github/workflows/         tests and release
```

No licence has been chosen yet; add a `LICENSE` file before sharing the code beyond this proof of concept.
