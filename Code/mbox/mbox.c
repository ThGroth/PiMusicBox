  GNU nano 2.2.6                                           Datei: mbox.c                                                                                              

#include <stdio.h>
#include <sys/time.h>
#include <wiringPi.h>

// Which GPIO pin we're using
#define BUTTONSTOP 0
#define BUTTONNEXT 2
#define BUTTONPAUSE 3

#define LEDON 1
#define LEDPAUSE 4
// How much time a change must be since the last in order to count as a change
#define IGNORE_CHANGE_BELOW_USEC 50000

// Current state of the pin
static volatile int state;

//should I stop?
static int stop;
// Time of last change
struct timeval last_change;

// Handler for interrupt
void handlenext(void) {
        struct timeval now;
        unsigned long diff;

        gettimeofday(&now, NULL);

        // Time difference in usec
        diff = (now.tv_sec * 1000000 + now.tv_usec) - (last_change.tv_sec * 1000000 + last_change.tv_usec);

        // Filter jitter
        if (diff > IGNORE_CHANGE_BELOW_USEC) {
                printf("Go to next title\n");
                state = !state;
                system("mpc next");
        }

        last_change = now;
}
void handlestop(void) {
        struct timeval now;
        unsigned long diff;

        gettimeofday(&now, NULL);

        // Time difference in usec
        diff = (now.tv_sec * 1000000 + now.tv_usec) - (last_change.tv_sec * 1000000 + last_change.tv_usec);

        // Filter jitter
        if (diff > IGNORE_CHANGE_BELOW_USEC) {
                printf("Stop program\n");
                stop = 1;
        }

        last_change = now;
}
void handlepause(void) {
        // Filter jitter
        sleep(0.5);
        state = digitalRead(BUTTONPAUSE);

        if(state) {
                printf("resume playing\n");
                system("mpc play");
                digitalWrite(LEDPAUSE,LOW);
        }
        else {
                printf("pause playing\n");
                system("mpc pause");
                digitalWrite(LEDPAUSE,HIGH);

        }
}

int main(void) {
        // Init
        wiringPiSetup();

        // Set pin to output in case it's not
        pinMode(BUTTONNEXT, INPUT);
        pinMode(BUTTONSTOP,INPUT);
        pinMode(LEDON,OUTPUT);
        pinMode(LEDPAUSE,OUTPUT);
        
        // Time now
        gettimeofday(&last_change, NULL);

        // Bind to interrupt
        wiringPiISR(BUTTONNEXT, INT_EDGE_FALLING, &handlenext);
        wiringPiISR(BUTTONSTOP, INT_EDGE_FALLING, &handlestop);
        wiringPiISR(BUTTONPAUSE, INT_EDGE_BOTH, &handlepause);

        digitalWrite(LEDPAUSE,LOW);
        digitalWrite(LEDON,HIGH);
        system("mpc play");
        // Waste time but not CPU
        stop=0;
        while (!stop) {
/*              state = digitalRead(BUTTONNEXT);
                printf(" read Now\n");
                if (state) {
                        printf("Button not pressed");
                }*/
                sleep(1);
        }
        system("mpc stop");
        digitalWrite(LEDPAUSE,HIGH);
        digitalWrite(LEDON,LOW);
        system("halt");
}


