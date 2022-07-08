#include<stdio.h>
#include<string.h>
#include<sys/socket.h>
#include<arpa/inet.h>
#include<sys/time.h>
#include<errno.h>

/*
 * Port Knocker
 *
 *     attempts connect() with 50ms timeout to an IP on a list of ports
 *     as an effective "port knock"
 *
 * Configure: replace PORTS with comma-separated list of ports
 *            update NPORTS with the number of ports
 *
 * Build:     gcc -static -o knock knock.c
 *
 * Run:       ./knock <IPADDR>
 */

#define assert(msg, ret, okval) { if (ret==okval) {fprintf(stderr, "%s %d\n", msg, errno); return 1;} }

#define TIMEOUT_MS 50
#define NPORTS __CHANGE_ME__
#define PORTS  __CHANGE_ME__
int ports[NPORTS] = {PORTS};

int main(int argc, char **argv) {
    if (argc < 2) {
        printf("usage: %s IPADDR\n", argv[0]);
        return 1;
    }
    int sockfd, ret;
    struct sockaddr_in addr;
    struct timeval t;

    memset(&t, 0, sizeof(t));
    t.tv_sec = 0;
    t.tv_usec = TIMEOUT_MS * 1000;

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    ret = inet_aton(argv[1], &addr.sin_addr);
    assert("inet_aton", ret, 0);

    for (int i = 0; i < NPORTS; i++) {
        fprintf(stderr, "trying port %d\n", ports[i]);
        addr.sin_port = htons(ports[i]);

        sockfd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        assert("socket", sockfd, -1);

        ret = setsockopt(sockfd, SOL_SOCKET, SO_SNDTIMEO, &t, sizeof(t));
        assert("setsockopt", ret, -1);

        ret = connect(sockfd, (struct sockaddr *) &addr, sizeof(addr));
        if (ret != -1) fprintf(stderr, "port %d is open %d\n", ports[i], ret);
        close(sockfd);
        if (ret != -1) break;
    }
    if (ret == -1) { printf("knock complete!\n"); }
    return 0;
}
