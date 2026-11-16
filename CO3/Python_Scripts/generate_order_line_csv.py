#!/usr/bin/env python3
"""Generate reproducible ShopNest ORDER_LINE source CSV for MySQL loading."""
import argparse, csv
from pathlib import Path
from run_experiments import row_values

HEADERS=['OrderID','OrderDate','CustomerID','CustomerName','CustomerEmail','ShipStreet','ShipCity','ShipPIN','ShipState','ProductID','ProductName','UnitPrice','CategoryID','CategoryName','SupplierID','SupplierName','SupplierPhone','Quantity','WarehouseID','WarehouseCity','TagList','ColourList']

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--rows',type=int,default=1000,help='number of order-line rows')
    parser.add_argument('--output',default='../Data/order_line_generated.csv')
    args=parser.parse_args()
    if args.rows<1: raise SystemExit('--rows must be positive')
    out=Path(args.output)
    if not out.is_absolute(): out=(Path(__file__).resolve().parent/out).resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(HEADERS)
        for i in range(args.rows): w.writerow(row_values(i))
    print(f'Generated {args.rows:,} order-line rows: {out}')

if __name__=='__main__': main()
