# Barcode

## Hipothesys
* Barcodes once generated are unique
* Plates are identified with barcodes as input or output of a process
* Barcode may be input in a station if are output of a precedeing station, following this stations: 0->A->B->C->PCR
* The same barcode can be read multiple times in the same station

## Implementation
In MBR templates are defined those task that need to read a barcode with the specification of the "type": input/output. If the plate is consumed it is an input, if it is produced it is an output.

The server return HTTP error or not if it is queried (with a PUT method) at this endpoint "/api/isbarcodeok/**station**/**runid**/**barcode**/**action**"
- **station**: is the station name where the barcode is read
- **runid**: is the identifier of that run
- **barcode**: the barcode value
- **action**: input/output value

Logic:

* action is input
  * Station is 0
    * Barcodes has already been scanned -> **Error**
    * Barcodes has not already been scanned -> **Succes**
  * Station is not 0
    * Barcode has been scanned in the previous station type as an output
      * Barcode is already used as input in another MBR -> **Error**
      * Otherwise -> **Success**
    * Otherwise -> **Error**
* action is output
  * Barcode has already been scanned
    * The barcode in the database has same run, station and action -> **Success**
    * Otherwise -> **Error**
  * Otherwise -> **Success**

Implementation is from line 145 - 180 of `app.py`.

## Barcode result

From the database following the procces flow as mentioned before we make the following joins:

1. Input barcodes in Protcol[n] are joined with output barcodes of Protocol[n] by run, i.e. the inputs of a run go in the ouput of the same run
2. Input barcodes of Protocol[n+1] are joined with ouput barcodes of Protocol[n], i.e. the input of a run comes from the output of a run of a preceiding Station

This join is iterated from the first station to the last.
Implementation is from line 182 - 196 of `app.py`.


