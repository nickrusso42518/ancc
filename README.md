# AI-based Network Configuration Converter (ANCC)
This project uses [OpenAI (GPT)](https://openai.com/) to convert network device
configurations between different operating systems and platforms. After the
conversion, it uses [Batfish](https://www.batfish.org/) to perform a cursory
validation of the converted configuration against the original. Last, it uses
[Cisco Modeling Language (CML)](https://www.cisco.com/c/en/us/products/cloud-systems-management/modeling-labs/index.html)
to simulate a network topology, furthering test the conversion result.

__Warning: This project is still under construction and should NOT be used
until this warning is rescinded.__

> Contact information:\
> Email:    njrusmc@gmail.com\
> Twitter:  @nickrusso42518

  * [Installation](#installation)
  * [Getting Started](#getting-started)

## Installation
  1. Deploy an Ubuntu Linux development box. You can use other
     distributions/operating systems, but step 2 will be different.
  2. Install Docker on Ubuntu Linux:
     `sudo ./install_docker_ubuntu.sh`
  3. Pull (download) desired version of Batfish from Dockerhub:
     `sudo docker pull batfish/allinone:2023.12.16.1270`
  4. Run a new Batfish container in the background:
     ```
     sudo docker container prune --force
     sudo docker container run --name batfish \
       --volume batfish-data:/data \
       --publish 8888:8888 --publish 9997:9997 --publish 9996:9996 \
       --detach batfish/allinone:2023.12.16.1270
     ```
  5. Export OpenAI API key, generated via the OpenAI website:
     `export OPENAI_API_KEY=sk-e...j5Or`

## Getting Started
  1. Clone this repository using HTTPS or SSH:
     `git clone <repo_url>`
  2. Install the required Python packages:
     `pip install -r requirements.txt`
  3. Run the script and specify a snapshot directory:
     `python bf.py brkrst3310`

## Dev Notes
