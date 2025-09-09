# syntax=docker/dockerfile:1


## Build a new Container by running:
##    docker buildx build -f .\Dockerfile -t linkedin-bot:1.0 --no-cache .

## start the container by performing: (--rm is to stop and remove the container after one turn)
##  docker run --rm --name linkedin-bot linkedin-bot:1.0
## 
## exposing the webUI Port 4561 to a local Port, mounting the config and content directorys with:
## docker run -p 4561:4561 -v <your favorite config directory>:/config -v <your favorite content directory>:/content -v <your favorite Logging directory>:/var/log --name linkedin-bot linkedin-bot:1.0
## 




ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Install Git to clone the private repository
RUN apt-get update && apt-get install -y git


WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

#COPY . .

EXPOSE 4561
RUN git clone https://github.com/opxon-andre/linkedin_ai_poster.git /app

### possible entrypoints:
    ## generate -> only generates new content
    ## automode -> takes the most recent content from the content/new directory, posts it to LI, and create a new post for the stack.
ENTRYPOINT ["python", "app/main.py", "scheduler"]








