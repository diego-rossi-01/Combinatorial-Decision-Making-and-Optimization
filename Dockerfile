FROM python:3.10
WORKDIR /app

# 1) installo wget, tar e le librerie per MiniZinc/Gecode
RUN apt-get update && apt-get install -y \
      wget \
      tar \
      libgl1-mesa-glx \
      libegl1-mesa \
    && rm -rf /var/lib/apt/lists/*

# 2) scarico ed estraggo il bundle MiniZinc 2.9.2
RUN wget -O minizinc.tgz \
      https://github.com/MiniZinc/MiniZincIDE/releases/download/2.9.2/MiniZincIDE-2.9.2-bundle-linux-x86_64.tgz \
 && mkdir -p /opt/minizinc \
 && tar -xzf minizinc.tgz -C /opt/minizinc --strip-components=1 \
 && rm minizinc.tgz \
 && ln -s /opt/minizinc/bin/minizinc   /usr/local/bin/minizinc \
 && ln -s /opt/minizinc/bin/mzn2fzn    /usr/local/bin/mzn2fzn \
 && ln -s /opt/minizinc/bin/fzn-gecode /usr/local/bin/fzn-gecode \
 && ln -s /opt/minizinc/bin/fzn-chuffed /usr/local/bin/fzn-chuffed

# 3) installo Python e pip
RUN apt-get update && apt-get install -y python3.10 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 4) copio tutta la repo in /app
COPY Instances /app/instances/
COPY output_instances /app/output_instances/
COPY . /app

# 5) installo le dipendenze Python
RUN pip3 install --no-cache-dir -r requirements.txt

# 6) Definisco CMD che lancia i due script in sequenza
# 6) Definisco CMD che lancia i due script in sequenza
ENTRYPOINT ["./entrypoint.sh"]
