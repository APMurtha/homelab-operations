/* The service manager supplies a connected socket. No path, verb, payload, or
 * destination comes from the caller. Revoke socket writes before parsing input. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <time.h>

#define GET(name, connection) "GET /v1.47/containers/" name "/json HTTP/1.1\r\nHost: localhost\r\nConnection: " connection "\r\n\r\n"
#define ROUND(last) GET("dispatcharr","keep-alive") GET("rivendell-iptv-gateway","keep-alive") GET("rivendell-iptv-vpn","keep-alive") GET("jellyfin",last)
static const char batch[] = ROUND("keep-alive") ROUND("close");

int main(int argc, char **argv) {
    (void)argv;
    struct timespec t;
    char timestamp[32];
    if (argc != 1 || clock_gettime(CLOCK_REALTIME, &t) != 0) return 1;
    snprintf(timestamp, sizeof(timestamp), "%lld%09ld", (long long)t.tv_sec, t.tv_nsec);
    const char *fds = getenv("LISTEN_FDS"), *names = getenv("LISTEN_FDNAMES");
    if (!fds || strcmp(fds, "1") || !names || strcmp(names, "engine")) return 1;
    size_t sent = 0;
    while (sent < sizeof(batch)-1) {
        ssize_t n = write(3, batch+sent, sizeof(batch)-1-sent);
        if (n <= 0) return 1;
        sent += (size_t)n;
    }
    if (shutdown(3, SHUT_WR) || dup2(3, STDIN_FILENO) < 0 || close_range(3, ~0U, 0)) return 1;
    execl("/usr/bin/python3", "python3", "-IB", "/opt/samwise-engine-health/acquire.py", timestamp, (char *)NULL);
    return 1;
}
