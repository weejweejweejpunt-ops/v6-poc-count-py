# This specifies our base image. This base image contains some commonly used
# dependancies and an install from all vantage6 packages. You can specify a
# different image here (e.g. python:3). In that case it is important that
# `vantage6-client` is a dependancy of you project as this contains the wrapper
# we are using in this example.
ARG BASE=5.0
FROM ghcr.io/vantage6/infrastructure/algorithm-base:${BASE}

# Links the image on ghcr.io to this repository. Without it a GitHub Actions workflow can create the package,
# but a later release may be refused write access to it.
LABEL org.opencontainers.image.source="https://github.com/weejweejweejpunt-ops/v6-poc-count-py"
LABEL org.opencontainers.image.description="vantage6 v5 proof of concept: federated count of rows per value of a column"

# Change this to the package name of your project. This needs to be the same
# as what you specified for the name in the `setup.py`.
ARG PKG_NAME="v6_poc_count"

# This will install your algorithm into this image.
COPY . /app
RUN uv pip install --system -e /app

# This will run your algorithm when the Docker container is started. The
# wrapper takes care of the IO handling (communication between node and
# algorithm). You dont need to change anything here.
ENV PKG_NAME=${PKG_NAME}
CMD python -c "from vantage6.algorithm.tools.wrap import wrap_algorithm; wrap_algorithm()"
