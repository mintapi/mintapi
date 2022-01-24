FROM selenium/standalone-chrome

# add mintapi to path
ENV PATH=$HOME/.local/bin:$PATH

RUN echo "**** install packages ****" && \
    sudo apt-get update && \
    sudo apt-get install -y python3-pip && \
    pip3 install mintapi && \
    echo "**** cleanup ****" && \
    sudo apt-get clean && \
    sudo rm -rf \
	/tmp/* \
	/var/lib/apt/lists/* \
	/var/tmp/*

# make mintapi help menu default command
CMD mintapi -h
