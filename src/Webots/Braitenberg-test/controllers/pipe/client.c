/*
 * File:         client.c
 * Date:         September 6th, 2006
 * Description:  A simple C program implementing a controller using the Unix
 *               pipe relay controller defined in pipe.c.
 * Author:       Simon Blanchoud
 * Modifications:
 *
 * Copyright (c) 2006 Cyberbotics - www.cyberbotics.com
 */

/* 
 * The protocole used in this example is taken from the Khepera serial       
 * communication protocole. Hence, if you already have developed an          
 * application which uses this protocole (and send the data over the serial  
 * port), you will just need to redirect the data to the pipe file of        
 * this controller to make it work with Webots.                              
 *                                                                           
 * compile it with "gcc client.c -o client"                                  
 * or "make -f Makefile.client"                                              
 *                                                                           
 * Everything relies on standard unix pipes.                                 
 */

#include <stdio.h>              /* definition of sprintf, fprintf, sscanf and stderr */
#include <string.h>             /* definition of strcpy() and strlen() */
#include <fcntl.h>              /* definition of O_RDONLY, O_NDELAY and O_WRONLY */
#include <stdlib.h>             /* definition of system() */
#include <unistd.h>             /* definition of sleep(), read() and write() */
#include "common.h"

int main()
{
    char a[256];
    unsigned short ds_value[NB_IR_SENSOR];
    int sim_serial_in, sim_serial_out;

    sim_serial_in = -1;
    sim_serial_out = -1;

    do {
        if (sim_serial_in == -1){
            sim_serial_in =
                open(PIPE_FILE_DIRECTORY ".sim_serial_in", O_WRONLY, 0);
        }
        if (sim_serial_out == -1){
            sim_serial_out =
                open(PIPE_FILE_DIRECTORY ".sim_serial_out", O_RDONLY, 0);
        }
        if ((sim_serial_in == -1 || sim_serial_out == -1)){
            fprintf(stderr, "client controller: cannot open pipes: %d %d, "
                    "keep trying\n", sim_serial_in, sim_serial_out);
        }
    } while (sim_serial_in == -1 || sim_serial_out == -1);

    /* move forward until a wall is reached */
    write(sim_serial_in, "D,10,10\n", strlen("D,10,10\n"));
    read(sim_serial_out, a, 256);   /* ignore "d\n" answer */

    for (;;) {
        write(sim_serial_in, "N\n", 3); /* read distance sensors */

        if (read(sim_serial_out, a, 256) != -1) {
            sscanf(a, "n,%hd,%hd,%hd,%hd,%hd,%hd,%hd,%hd",
                   &ds_value[0],
                   &ds_value[1],
                   &ds_value[2],
                   &ds_value[3],
                   &ds_value[4], &ds_value[5], &ds_value[6], &ds_value[7]);
            if (ds_value[2] > 100 || ds_value[3] > 100) {
                write(sim_serial_in, "D,0,0\n", strlen("D,0,0\n"));
                read(sim_serial_out, a, 256);   /* ignore "d\n" answer */
                printf("stopped in front of the wall\n");
            } else {
                printf("going forward\n");
            }
        }
    }

    return 0;
}
