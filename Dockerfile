FROM python:3.13

RUN wget https://github.com/wolfSSL/wolfssl/archive/refs/tags/v5.8.2-stable.tar.gz -O wolfssl-v5.8.2.tar.gz && \
    tar -xf wolfssl-v5.8.2.tar.gz && \
    cd wolfssl-5.8.2-stable && \
    ./autogen.sh && \
    ./configure CFLAGS="-DDTLS_CID_MAX_SIZE=8 -DWOLFSSL_ALWAYS_VERIFY_CB" --enable-all --enable-debug --enable-secure-renegotiation --enable-sni --enable-dtls --enable-dtls13 --enable-dtlscid --enable-ipv6 --enable-rpk && \
    make -j && \
    make install && \
    cd .. && \
    rm wolfssl-v5.8.2.tar.gz && \
    rm -rf wolfssl-5.8.2-stable

ENV LD_LIBRARY_PATH=/usr/local/lib

RUN mkdir /app && useradd app
WORKDIR /app
RUN pip install -U pip

COPY requirements.txt /app/
RUN pip install -r requirements.txt

RUN apt update && apt install iproute2 -y

USER app:app

COPY manage.py /app/manage.py
COPY tappybara /app/tappybara
COPY asn1 /app/asn1
COPY coap_server /app/coap_server
COPY pos_server /app/pos_server
COPY vas /app/vas