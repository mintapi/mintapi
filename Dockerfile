FROM ubuntu:xenial

RUN apt-get update -yq

# Dependencies to make "headless" chrome/selenium work:
RUN apt-get -y install xorg xvfb gtk2-engines-pixbuf
RUN apt-get -y install dbus-x11 xfonts-base xfonts-100dpi xfonts-75dpi xfonts-cyrillic xfonts-scalable

RUN apt-get install -y git wget curl vim unzip python python-setuptools chromium-chromedriver \
    pandoc sudo python-dbus xvfb

# Install Chromium.
RUN apt-get -y install libxpm4 libxrender1 libgtk2.0-0 libnss3 libgconf-2-4

RUN \
  wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
  echo "deb http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list && \
  apt-get update && \
  apt-get install -y google-chrome-stable

# Install ChromeDriver.
RUN \
  CHROME_DRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`  && \
  wget -N http://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip -P ~/ && \
  unzip ~/chromedriver_linux64.zip -d ~/ && \
  rm ~/chromedriver_linux64.zip && \
  mv -f ~/chromedriver /usr/local/bin/chromedriver && \
  chown root:root /usr/local/bin/chromedriver && \
  chmod 0755 /usr/local/bin/chromedriver

RUN rm -rf /var/lib/apt/lists/*

RUN python --version

RUN easy_install pip

RUN pip install secretstorage keyring

RUN useradd -ms /bin/bash -u 1001 appuser
RUN echo 'appuser:appuser' | chpasswd
RUN usermod -a -G sudo appuser
USER appuser

RUN mkdir -p /home/appuser/mintapi/
WORKDIR /home/appuser/mintapi/

COPY . /home/appuser/mintapi/

RUN whoami && pwd && env

RUN pip install selenium --user
RUN pip install pypandoc --user

RUN python setup.py install --user
RUN echo 'export PATH=$HOME/.local/bin/:$PATH' >> ~/.bash_profile
#RUN python mintapi/api.py

