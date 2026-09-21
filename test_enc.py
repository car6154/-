
import sys
line = open('autoplus_inventory.csv', 'r', encoding='utf-8-sig').readline()
sys.stdout.buffer.write(line.encode('utf-8'))
