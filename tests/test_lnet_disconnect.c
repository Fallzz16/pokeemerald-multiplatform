/* Regression: closing a peer with a pending slot must never strand the game.
 * Run with the native Linux LAN transport suite (real localhost TCP).
 */
#include "lnet_session.h"
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <unistd.h>

#define TEST_PORT 45677
static int hostResult = -99;
static int clientResult = -99;

static void *host_thread(void *ignored)
{
    int err = 0;
    int result = 0;
    unsigned short peer = 0;
    LNetSession *s;
    (void)ignored;
    s = lnet_session_host(TEST_PORT, &err);
    if (!s)
    {
        hostResult = -10;
        return NULL;
    }
    while (!lnet_session_is_ready(s))
    {
        if (lnet_session_poll(s, &err) < 0)
        {
            hostResult = -11;
            lnet_session_close(s);
            return NULL;
        }
        sched_yield();
    }
    do
    {
        result = lnet_session_exchange(s, 0xFACE, &peer);
        if (result == 0)
            usleep(1000);
    } while (result == 0);
    hostResult = result;
    lnet_session_close(s);
    return NULL;
}

static void *client_thread(void *ignored)
{
    int err = 0;
    LNetSession *s;
    (void)ignored;
    /* Give the server a chance to bind before attempting connection. */
    usleep(30000);
    s = lnet_session_join("127.0.0.1", TEST_PORT, &err);
    if (!s)
    {
        clientResult = -10;
        return NULL;
    }
    while (!lnet_session_is_ready(s))
    {
        if (lnet_session_poll(s, &err) < 0)
        {
            clientResult = -11;
            lnet_session_close(s);
            return NULL;
        }
        sched_yield();
    }
    /* Send no SIO response: simulate device exit during first slot. */
    usleep(150000);
    clientResult = 1;
    lnet_session_close(s);
    return NULL;
}

int main(void)
{
    pthread_t host, client;
    if (pthread_create(&host, NULL, host_thread, NULL) != 0)
        return 2;
    if (pthread_create(&client, NULL, client_thread, NULL) != 0)
        return 2;
    pthread_join(host, NULL);
    pthread_join(client, NULL);
    if (hostResult != -1 || clientResult != 1)
    {
        fprintf(stderr, "FAIL: closed peer must end pending SIO exchange (host=%d client=%d)\n", hostResult, clientResult);
        return 1;
    }
    /* Hostnames and malformed IPv4 strings must be rejected immediately.
     * Blocking gethostbyname() in the game thread is not acceptable. */
    {
        const char *invalid[] = {"example.invalid", "256.1.2.3", "not-an-ip"};
        int i;
        for (i = 0; i < 3; i++)
        {
            int err = LNET_ERR_OK;
            int result;
            LNetSession *bad = lnet_session_join(invalid[i], TEST_PORT, &err);
            if (!bad)
                return 3;
            result = lnet_session_poll(bad, &err);
            lnet_session_close(bad);
            if (result != -1 || err != LNET_ERR_CONNECT)
            {
                fprintf(stderr, "FAIL: invalid IPv4 was accepted: %s (result=%d err=%d)\n", invalid[i], result, err);
                return 1;
            }
        }
    }
    puts("passed: peer disconnect detected during incomplete slot; invalid IPv4 rejected");
    return 0;
}
