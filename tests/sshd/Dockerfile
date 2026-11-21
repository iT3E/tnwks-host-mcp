# The fake host of the image test: OpenSSH with one normal user, agent, and
# key sign-in only. The test makes the keys at its start and mounts them;
# no key is in git. A file that only root reads tests the rights of the user.
FROM alpine:3.20@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc
RUN apk add --no-cache openssh-server openssh-keygen bash coreutils procps \
 && adduser -D -s /bin/bash agent \
 && (passwd -u agent >/dev/null 2>&1 || true) \
 && echo "root only" > /etc/test-root-only && chmod 600 /etc/test-root-only \
 && echo "test host ok" > /etc/test-motd && chmod 644 /etc/test-motd
COPY sshd_config /etc/ssh/sshd_config
EXPOSE 22
CMD ["/usr/sbin/sshd", "-D", "-e"]
