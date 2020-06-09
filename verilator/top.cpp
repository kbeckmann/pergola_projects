#include <stdio.h>
#include <stdlib.h>
#include "obj_dir/Vtop.h"
#include "verilated.h"

/**

python -m pergola sim blinky
verilator -Wall -cc top.debug.v --public
g++ -I obj_dir \
    /usr/share/verilator/include/verilated.cpp \
    top.cpp \
    obj_dir/Vtop.cpp \
    obj_dir/Vtop__Syms.cpp  \
    -I /usr/share/verilator/include \
    -o top.elf

*/

int main(int argc, char *argv[])
{
    Verilated::commandArgs(argc, argv);

    Vtop *top = new Vtop;

    for (int i = 0; i < 100; i++) {
        top->clk16_0___05Fio = ~top->clk16_0___05Fio;

        top->eval();

        printf("%d\n", top->top__DOT__blinky__DOT__timer);
    }
    return 0;
}