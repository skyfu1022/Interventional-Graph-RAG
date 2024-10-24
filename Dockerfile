# Use a base image with Conda
FROM continuumio/miniconda3

# Set the working directory in the container
WORKDIR /app

# Copy the environment YAML file into the Docker image
COPY medgraphrag.yml .

RUN conda config --append channels conda-forge

# Create the Conda environment inside the Docker container
RUN conda env create -f medgraphrag.yml

# Make sure the environment is activated and Conda commands are available
RUN echo "source activate camelgym" > ~/.bashrc
SHELL ["/bin/bash", "--login", "-c"]

# Copy the rest of the application code into the Docker image
COPY . .

# Specify the command to run your application
CMD ["python", "run.py"]
