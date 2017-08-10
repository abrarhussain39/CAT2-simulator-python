#! python
# (c) DL, UTA, 2009 - 2016
import  sys, string, time
import math
wordsize = 24                                        # everything is a word
numregbits = 3                                       # actually +1, msb is indirect bit
opcodesize = 5
addrsize = wordsize - (opcodesize+numregbits+1)      # num bits in address
memloadsize = 1024                                   # change this for larger programs
numregs = 2**numregbits
regmask = (numregs*2)-1                              # including indirect bit
addmask = (2**(wordsize - addrsize)) -1
nummask = (2**(wordsize))-1
opcposition = wordsize - (opcodesize + 1)            # shift value to position opcode
reg1position = opcposition - (numregbits +1)            # first register position
reg2position = reg1position - (numregbits +1)
memaddrimmedposition = reg2position                  # mem address or immediate same place as reg2
realmemsize = memloadsize * 1                        # this is memory size, should be (much) bigger than a program
#memory management regs
codeseg = numregs - 1                                # last reg is a code segment pointer
dataseg = numregs - 2                                # next to last reg is a data segment pointer
#ints and traps
trapreglink = numregs - 3                            # store return value here
trapval     = numregs - 4                            # pass which trap/int
mem = [0] * realmemsize                              # this is memory, init to 0 
reg = [0] * numregs                                  # registers
clock = 1                                            # clock starts ticking
ic = 0                                               # instruction count
numcoderefs = 0                                      # number of times instructions read
numdatarefs = 0                                      # number of times data read
starttime = time.time()
curtime = starttime
#change the value of col1 and row1 for different cache sizes 4,4
coll1=2
rowl1=4
coll2=8
rowl2=8
tagl1=[0]*rowl1
validl1=[0]*rowl1
tagl2=[0]*rowl2
validl2=[0]*rowl2
l1hit=0
l2hit=0
memhit=0
#declaring cache arrays
cachearrayl1=[[0 for i in range (coll1)] for j in range (rowl1)]
cachearrayl2=[[0 for i in range(coll2)] for j in range(rowl2)]

def startexechere ( p ):
    # start execution at this address
    reg[ codeseg ] = p    
def loadmem():                                       # get binary load image
  curaddr = 0
  for line in open("a.out", 'r').readlines():
    token = string.split( string.lower( line ))      # first token on each line is mem word, ignore rest
    if ( token[ 0 ] == 'go' ):
        startexechere(  int( token[ 1 ] ) )
    else:    
        mem[ curaddr ] = int( token[ 0 ], 0 )                
        curaddr = curaddr = curaddr + 1
def getcodemem ( a ):
    # get code memory at this address
    #memval = mem[ a + reg[ codeseg ] ]
    memval=getfroml1cache(a + reg[ codeseg ])
    return ( memval )
def getdatamem ( a ):
    # get code memory at this address
    #memval = mem[ a + reg[ dataseg ] ]
    memval=getfroml1cache(a + reg[ dataseg ])
    return ( memval )
    #function for l1 cache
def getfroml1cache(addr):
    global l1hit

    binformat= '{:015b}'.format(addr)
    colbit=int(math.log(coll1,2))
    rowbit=int(math.log(rowl1,2))
    tagbit = addrsize-(colbit+rowbit)
    tagvalue= int(binformat[0:tagbit],2)

    rowvalue= int(binformat[tagbit: tagbit+rowbit],2)
    wordvalue = int(binformat[tagbit+rowbit:addrsize],2)
    if(validl1[rowvalue]==1) and (tagl1[rowvalue]==tagvalue):
      l1hit+=1
      return cachearrayl1[rowvalue][wordvalue]
    else:
      
      tempaddr = addr>>colbit
      naddr = tempaddr<<colbit
      for i in range (0,coll1):
        cachearrayl1[rowvalue][i]=getfroml2cache(naddr+i)
      tagl1[rowvalue]=tagvalue
      validl1[rowvalue]=1
      return cachearrayl1[rowvalue][wordvalue]
      #function for l2 cache
def getfroml2cache(addr):
    global l2hit
    global memhit
    binformat= '{:014b}'.format(addr)
    colbit=int(math.log(coll2,2))
    rowbit=int(math.log(rowl2,2))
    tagbit = addrsize-(colbit+rowbit)
    tagvalue= int(binformat[0:tagbit],2)
    rowvalue= int(binformat[tagbit: tagbit+rowbit],2)
    wordvalue = int(binformat[-(colbit):],2)
    if(validl2[rowvalue]) and (tagl2[rowvalue]==tagvalue):
      l2hit+=1
      return cachearrayl2[rowvalue][wordvalue]
    else:
      memhit+=1
      memvalue = mem[addr]
      tempaddr = addr>>colbit
      naddr = tempaddr<<colbit
      tagl2[rowvalue]=tagvalue
      validl2[rowvalue]=1
      vals = [0]*coll2
      for i in range (0,coll2):
        cachearrayl2[rowvalue][i]=mem[naddr+i]
      return cachearrayl2[rowvalue][wordvalue]





def getregval ( r ):
    # get reg or indirect value
    if ( (r & (1<<numregbits)) == 0 ):               # not indirect
       rval = reg[ r ] 
    else:
       rval = getdatamem( reg[ r - numregs ] )       # indirect data with mem address
    return ( rval )
def checkres( v1, v2, res):
    v1sign = ( v1 >> (wordsize - 1) ) & 1
    v2sign = ( v2 >> (wordsize - 1) ) & 1
    ressign = ( res >> (wordsize - 1) ) & 1
    if ( ( v1sign ) & ( v2sign ) & ( not ressign ) ):
      return ( 1 )
    elif ( ( not v1sign ) & ( not v2sign ) & ( ressign ) ):
      return ( 1 )
    else:
      return( 0 )
def dumpstate ( d ):
    if ( d == 1 ):
        print reg
    elif ( d == 2 ):
        print mem
    elif ( d == 3 ):
        print 'clock=', clock, 'IC=', ic, 'Coderefs=', numcoderefs,'Datarefs=', numdatarefs, 'Start Time=', starttime, 'Currently=', time.time()
        #printing cache details
        print 'l1 cache =',cachearrayl1
        print 'l2 cache =',cachearrayl2
        print 'l1 hit =',l1hit,'  l2 hit =',l2hit,'  memory hit =',memhit
def trap ( t ):
    # unusual cases
    # trap 0 illegal instruction
    # trap 1 arithmetic overflow
    # trap 2 sys call
    # trap 3+ user
    rl = trapreglink                            # store return value here
    rv = trapval
    if ( ( t == 0 ) | ( t == 1 ) ):
       dumpstate( 1 )
       dumpstate( 2 )
       dumpstate( 3 )
    elif ( t == 2 ):                          # sys call, reg trapval has a parameter
       what = reg[ trapval ] 
       if ( what == 1 ):
           a = a        #elapsed time
    return ( -1, -1 )
    return ( rv, rl )
# opcode type (1 reg, 2 reg, reg+addr, immed), mnemonic  
opcodes = { 1: (2, 'add'), 2: ( 2, 'sub'), 
            3: (1, 'dec'), 4: ( 1, 'inc' ),
            7: (3, 'ld'),  8: (3, 'st'), 9: (3, 'ldi'),
           12: (3, 'bnz'), 13: (3, 'brl'),
           14: (1, 'ret'),
           16: (3, 'int') }
startexechere( 0 )                                  # start execution here if no "go"
loadmem()                                           # load binary executable
ip = 0                                              # start execution at codeseg location 0
# while instruction is not halt
while( 1 ):
   ir = getcodemem( ip )                            # - fetch
   ip = ip + 1
   opcode = ir >> opcposition                       # - decode
   reg1   = (ir >> reg1position) & regmask
   reg2   = (ir >> reg2position) & regmask
   addr   = (ir) & addmask
   ic = ic + 1
                                                    # - operand fetch
   if not (opcodes.has_key( opcode )):
      tval, treg = trap(0) 
      if (tval == -1):                              # illegal instruction
         break
   memdata = 0                                      #     contents of memory for loads
   if opcodes[ opcode ] [0] == 1:                   #     dec, inc, ret type
      operand1 = getregval( reg1 )                  #       fetch operands
   elif opcodes[ opcode ] [0] == 2:                 #     add, sub type
      operand1 = getregval( reg1 )                  #       fetch operands
      operand2 = getregval( reg2 )
   elif opcodes[ opcode ] [0] == 3:                 #     ld, st, br type
      operand1 = getregval( reg1 )                  #       fetch operands
      operand2 = addr                     
   elif opcodes[ opcode ] [0] == 0:                 #     ? type
      break
   if (opcode == 7):                                # get data memory for loads
      memdata = getdatamem( operand2 )
   # execute
   if opcode == 1:                     # add
      result = (operand1 + operand2) & nummask
      if ( checkres( operand1, operand2, result )):
         tval, treg = trap(1) 
         if (tval == -1):                           # overflow
            break
   elif opcode == 2:                   # sub
      result = (operand1 - operand2) & nummask
      if ( checkres( operand1, operand2, result )):
         tval, treg = trap(1) 
         if (tval == -1):                           # overflow
            break
   elif opcode == 3:                   # dec
      result = operand1 - 1
   elif opcode == 4:                   # inc
      result = operand1 + 1
   elif opcode == 7:                   # load
      result = memdata
   elif opcode == 9:                   # load immediate
      result = operand2
   elif opcode == 12:                  # conditional branch
      result = operand1
      if result <> 0:
         ip = operand2
   elif opcode == 13:                  # branch and link
      result = ip
      ip = operand2
   elif opcode == 14:                   # return
      ip = operand1
   elif opcode == 16:                   # interrupt/sys call
      result = ip
      tval, treg = trap(reg1)
      if (tval == -1):
        break
      reg1 = treg
      ip = operand2
   # write back
   if ( (opcode == 1) | (opcode == 2 ) | 
         (opcode == 3) | (opcode == 4 ) ):     # arithmetic
        reg[ reg1 ] = result
   elif ( (opcode == 7) | (opcode == 9 )):     # loads
        reg[ reg1 ] = result
   elif (opcode == 13):                        # store return address
        reg[ reg1 ] = result
   elif (opcode == 16):                        # store return address
        reg[ reg1 ] = result
   # end of instruction loop     
# end of execution

   
