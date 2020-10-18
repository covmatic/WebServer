from flask_cors import CORS
from pathlib import Path
import uuid
import json
import glob
import logging
import os
from flask import Flask, request, render_template, abort
import datetime
import pandas as pd
import hashlib
import base64
from functools import wraps
barcode_stations_flow = ['api','station0','stationA','stationB','stationC','PCR']

if os.path.isfile('data/users.json'):
  with open('data/users.json', 'r') as f:
    users = json.load(f)
else:
  users=[]  

with open('stations/protocols.json', 'r') as f:
  protocols = json.load(f)

mapping = pd.read_csv('mapping.csv')


def isAuth(roles):
  if len(users):
    if not 'Authorization' in request.headers:
      return False
    try:
      username, pw = base64.b64decode(request.headers['Authorization'].split(' ')[1]).decode('utf-8').split(':')
      idx = [user['username'] for user in users].index(username)
      if users[idx]['password'] == hashlib.sha256(pw.encode()).hexdigest() and users[idx]['role'] in roles:
        return True
      else:
        return False
    except:
      return False
  else:
    return True


def admin(f):
  @wraps(f)
  def decorated_function(*args, **kws):
    if isAuth(['admin']):
      return f(*args, **kws)
    else:
      abort(401)
  return decorated_function

def biotech(f):
  @wraps(f)
  def decorated_function(*args, **kws):
    if isAuth(['biotech','admin']):
      return f(*args, **kws)
    else:
      abort(401)
  return decorated_function

def technician(f):
  @wraps(f)
  def decorated_function(*args, **kws):
    if isAuth(['technician', 'biotech', 'admin']):
      return f(*args, **kws)
    else:
      abort(401)
  return decorated_function

logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s]: {} %(levelname)s %(message)s'.format(os.getpid()),
                    datefmt='%Y-%m-%d %H:%M:%S',
                    handlers=[logging.StreamHandler()])

logger = logging.getLogger()
os.makedirs('data/mbr/partial', exist_ok=True)
os.makedirs('data/mbr/finished', exist_ok=True)
os.makedirs('data/mbr/approved', exist_ok=True)
os.makedirs('data/barcodes', exist_ok=True)
os.makedirs('data/approvals', exist_ok=True)

def create_app():
    app = Flask(__name__)
    CORS(app)

    @app.route("/api/whoami", methods = ['GET'])
    def whoami():
      if request.method == 'GET':
        if len(users):
          try:
            username = base64.b64decode(request.headers['Authorization'].split(' ')[1]).decode('utf-8').split(':')[0]
            data = users[[user['username'] for user in users].index(username)]
            return json.dumps(data), 200, {'ContentType':'application/json'}
          except:
            abort(401)
        else:
          return json.dumps({"username": "Anonymous", "name": "Anonymous", "surname": "Anonymous", "role": "admin"}), 200, {'ContentType':'application/json'}

    @app.route("/api/roles", methods = ['GET'])
    @admin
    def getRoles():
      if request.method=='GET':
        return json.dumps(['admin', 'biotech', 'technician'])

    @app.route("/api/users", methods = ['GET','PUT'])
    @app.route("/api/users/<username>", methods = ['DELETE'])
    @admin
    def usersManagement(username = None):
      global users
      if request.method == 'GET':
        if len(users):
          return pd.DataFrame(users).drop(columns='password').to_json(orient='records'), 200, {'ContentType':'application/json'}
        else:
          return json.dumps(users), 200, {'ContentType':'application/json'}
      elif request.method == 'PUT':
        user_to_add = request.json
        try:
          idx = [user['username'] for user in users].index(user_to_add['username'])
          users[idx]['name']=user_to_add['name']
          users[idx]['surname']=user_to_add['surname']
          users[idx]['role']=user_to_add['role']
          users[idx]['password']= hashlib.sha256(user_to_add['password'].encode()).hexdigest()
        except:
          users.append({})
          users[-1]['username']=user_to_add['username']
          users[-1]['name']=user_to_add['name']
          users[-1]['surname']=user_to_add['surname']
          users[-1]['role']=user_to_add['role']
          users[-1]['password']= hashlib.sha256(user_to_add['password'].encode()).hexdigest()
        with open('data/users.json', 'w+') as f:
          json.dump(users, f)
        return '', 200
      elif request.method == 'DELETE':
        try:
          idx = [user['username'] for user in users].index(username)
          users = users[:idx] + users[idx+1:]
          with open('data/users.json', 'w+') as f:
            json.dump(users, f)
          return '', 200
        except:
          return '', 400

    @app.route("/api/stations", methods = ['GET'])
    @technician
    def stations():
      if request.method == 'GET':
        if os.path.isfile('data/calibration.json'):
          with open('data/calibration.json', 'r') as f:
            calibration = json.load(f)
        else:
          calibration = {}
        res = []
        for prt in protocols:
          item = {}
          item['protocol'] = prt
          item['stations'] = []
          for s in protocols[prt]['stations']:
            if s in calibration:
              item['stations'].append({'name': s , "calibrated": calibration[s]==pd.Timestamp('now').floor('d').isoformat()})
            else:
              item['stations'].append({'name': s , "calibrated": False})
          res.append(item)
        return json.dumps(res), 200, {'ContentType':'application/json'}

    @app.route("/api/calibration/<station>", methods = ['PUT','GET'])
    @technician
    def calibration(station):
      if request.method == 'PUT':
        if os.path.isfile('data/calibration.json'):
          with open('data/calibration.json', 'r') as f:
            calibration = json.load(f)
        else:
          calibration = {}
        calibration[station] = pd.Timestamp('now').floor('d').isoformat()
        with open('data/calibration.json', 'w+') as f:
          json.dump(calibration, f)
        return '', 200
      elif request.method == 'GET':
        if os.path.isfile('data/calibration.json'):
          with open('data/calibration.json', 'r') as f:
            calibration = json.load(f)
          if station in calibration:
            return str(int(calibration[station]==pd.Timestamp('now').floor('d').isoformat())), 200
          else:
            return '0', 200
        else:
          return '0', 200

    def loadMBRTemplate(mbrTemplate):
      start_dict = {"name":"New Master Batch Record"
      ,"tasks":[{"name":"Get a new runID"
      ,"instructions":[{"name":"Start a new run"
      ,"action" : "newrun"}]}]}
      if mbrTemplate != 'station0.json':
        with open("stations/{}".format(mbrTemplate),'r', encoding="utf8") as f:
          data = json.load(f)
          data = [start_dict] + data
      else:
        sender_id = {"name":"Sender ID"
          ,"tasks":[{"name": "Scan the sender ID"
          ,"instructions": [{"name": "Sender ID",
              "isInput": 1
              }],
          "input": "sender"}]}
        
        def scanRack(rack_number):
          return {"name": "Scan the barcode on rack " + str(rack_number)
          ,"instructions": [{"name": "barcode",
              "isInput":1}],
              "input": "barcode",
              "endpoint": "output"}

        def scanPatients(df):
          tasks = []
          for _, row in df.iterrows():
            if row['is_nec']:
              tasks.append({"name":"Add negative control","instructions":[
                {"name": "place in A1 a blank collection tube, i.e. a collection tube only containing the medium in which no swabs have been placed"},
                {"name": "open the tube"}
              ]})
            elif row['is_pct']:
              tasks.append({"name":"Leave positive control empty","instructions":[{"name" : "leave position A1 empty"}]})
            else:
              tasks.append({"name": "Scan the patient barcode"
            ,"instructions": [
              {"name": "clean tube external surface with alcohol"},
              {"name": "barcode",
              "isInput":1}
                ,{"name": "Put the tube in position " + row['rack_position']},
              {"name" : "open the tube"}
              ],
               "input": "barcode",
                "endpoint": "input/" + barcode_stations_flow[0],
                "rackPosition": row['rack_position']})
          return tasks

        def getNewRunID(rack):
          if rack == 1:
            return []
          else:
            return [{"name":"New Rack"
            ,"instructions":[{"name":"Get a new run id"
                      ,"action" : "getnewrunid"}]}]

        fill_racks = [ {"name":"Fill rack " +str(rack)
          ,"tasks" :getNewRunID(rack) + [scanRack(rack)] + scanPatients(df) + [scanRack(rack)]}
        for rack, df in mapping.groupby('rack_number')]
        data = [start_dict] + [sender_id] + fill_racks
      return data

    @app.route("/api/protocol/<string:protocol>", methods = ['GET'])
    @technician
    def getProtocol(protocol):
      if request.method == 'GET':
        data = loadMBRTemplate(protocols[protocol]['mbrTemplate'])
        return json.dumps(data), 200, {'ContentType':'application/json'}

    @app.route("/api/station/<string:station>", methods = ['GET'])
    @technician
    def getProtocoForStation(station):
      if request.method == 'GET':
        for protocol in protocols.keys():
          if station in protocols[protocol]['stations']:
            data = loadMBRTemplate(protocols[protocol]['mbrTemplate'])
        return json.dumps(data), 200, {'ContentType':'application/json'}

    @app.route("/api/mbr", defaults={'run_id': None, 'station': None, 'status': None}, methods = ['GET'])
    @app.route("/api/mbr/<station>", defaults={'run_id': None, 'status': None}, methods = ['POST'])
    @app.route("/api/mbr/<status>", defaults={'run_id': None, 'station': None}, methods = ['GET'])
    @app.route("/api/mbr/<status>/<station>", defaults={'run_id': None}, methods = ['GET'])
    @app.route("/api/mbr/<status>/<station>/<run_id>", methods = ['GET', 'PATCH'])
    @technician
    def mbr(station,run_id,status):
      if request.method == 'POST':
        unique_filename = str(uuid.uuid4())
        with open('data/mbr/partial/' + station + "_" + unique_filename+'.json','w+') as f:
            json.dump([],f)
        return json.dumps({'runId':unique_filename}), 200, {'ContentType':'application/json'}
      elif request.method == 'GET':
        if run_id is not None:
          with open('data/mbr/{}/'.format(status) + station + "_" + run_id +'.json','r') as f:
            data = json.load(f)
            return json.dumps(data), 200, {'ContentType':'application/json'}
        else:
          files = glob.glob("data/mbr/{}/*.json".format(status))
          if station is not None:
            files = [f for f in files if Path(f).name[:-5].split('_')[0] in protocols[station]['stations']]
          return json.dumps([{'station': Path(f).name[:-5].split('_')[0]
          ,'runId':Path(f).name[:-5].split('_')[1]
          ,'timestamp':str(datetime.datetime.fromtimestamp(Path(f).lstat().st_mtime))} for f in files]), 200, {'ContentType':'application/json'}
      elif request.method == 'PATCH':
        values = request.json
        if ('endpoint' in values) and (values['input']=='barcode'):
          if '/' in values['endpoint']:
            action, protocol = values['endpoint'].split('/')
            if protocol!= barcode_stations_flow[0]:
              previous_station = protocols[protocol]['protocolName']
            else:
              previous_station = barcode_stations_flow[0]
          else:
            action = values['endpoint']
            previous_station = None
          barcode = values['result']
          msg, status = isbarcodeok(station,run_id,barcode,action, previous_station)
          if status != 200:
            return msg, status
        with open('data/mbr/partial/' + station + '_' + run_id + '.json','r') as f:
          data = json.load(f)
        values['timestamp'] = pd.Timestamp('now',tz='UTC').isoformat()
        user = getUser(request.headers['Authorization'])
        values['operator'] = user['name'] + ' ' + user['surname']
        data.append(values)
        with open('data/mbr/partial/' + station + '_' + run_id + '.json','w') as f:
          json.dump(data,f, indent=4)
        return json.dumps({'success': True}), 200, {'ContentType':'application/json'}

    def getUser(auth_header):
      if len(users):
        username = base64.b64decode(auth_header.split(' ')[1]).decode('utf-8').split(':')[0]
        return users[[user['username'] for user in users].index(username)]
      else:
        return {"username": "Anonymous", "name": "Anonymous", "surname": "Anonymous", "role": "admin"}

    @app.route("/api/mbr/approve/<station>/<run_id>", methods = ['PUT'])
    @biotech
    def approve(station,run_id):
      if request.method == 'PUT':
        user = getUser(request.headers['Authorization'])
        with open('data/approvals/{user}_{runid}_{time}'.format(user = user['username'], runid = run_id, time = pd.Timestamp('now').strftime("%Y%m%d%H%M%S")), 'w+') as f:
          f.close()
        os.system('mv data/mbr/finished/{}_{}.json data/mbr/approved'.format(station,run_id))
        return '',200

    def getPCRResult(pcrbarcode,position):
      barcode = glob.glob('data/barcodes/PCR_*_{}_input'.format(pcrbarcode))
      runid = barcode[0].split('_')[1]
      mbr_path = glob.glob('data/mbr/*/*{}.json'.format(runid))
      with open(mbr_path[0], 'r') as f:
        mbr = json.load(f)
      for idx,el in enumerate(mbr):
        if el['name']=='Run initialization':
          break
      for idx1, result in enumerate(mbr[idx]['result']['Wells']):
        if result['wellNum']==position:
          break
      return mbr, idx, idx1

    @app.route("/api/mbr/validator/<file_name>", methods = ['GET'])
    @biotech
    def getValidatorData(run_id):
      if request.method == 'GET':
        approval_data = Path(glob.glob('data/approvals/*_{}_*'.format(run_id))[0]).name
        user = [user for user in users if user['username']==approval_data.split('_')[0]][0]
        return json.dumps({'validator': ' '.join([user['name'],user['surname']]), 'timestamp': pd.to_datetime(approval_data.split('_')[2],format = "%Y%m%d%H%M%S").isoformat()}), 200, {'ContentType':'application/json'}

    @app.route("/api/mbr/finish/<station>/<run_id>", methods = ['PUT'])
    @technician
    def finish(station,run_id):
      if request.method == 'PUT':
        os.system('mv data/mbr/partial/{}_{}.json data/mbr/finished'.format(station,run_id))
        return '',200

    def checkPatientBarcode(barcode):
      df = getBarcodeDF()
      return barcode in df['barcode'][df['station'] == barcode_stations_flow[0]].values
    
    def getBarcodeDF():
      barcodes = glob.glob('data/barcodes/*')
      return pd.DataFrame([os.path.split(bc)[-1].split('_') for bc in barcodes], columns=['station','runid','barcode','action'])

    def addBarcode(station, runid, barcode, action):
      open('data/barcodes/{}_{}_{}_{}'.format(station,runid,barcode,action), 'w+').close()

    @app.route("/api/addpatientbarcodes", methods = ['POST'])
    @biotech
    def addPatientBarcodes():
      if request.method == 'POST':
        barcodes_to_add = request.json['barcodes']
        df = getBarcodeDF()
        duplicated_barcode = [barcode for barcode in request.json['barcodes'] if barcode in df['barcode'][df['station'] == barcode_stations_flow[0]].values]
        if len(duplicated_barcode):
          return 'Duplicated barcode: '+', '.join(duplicated_barcode), 400
        else:
          req_id = str(uuid.uuid4())
          [addBarcode(barcode_stations_flow[0] ,req_id, barcode, 'output') for barcode in barcodes_to_add]
          return req_id, 200

    def isbarcodeok(station,runid,barcode,action, previous_station = None):
      stations = {station:{'protocol':protocol,'mbrTemplate': protocols[protocol]['mbrTemplate'], 'protocolName': protocols[protocol]['protocolName']} for protocol in protocols for station in protocols[protocol]['stations']}
      station = stations[station]['protocolName']
      if barcode[:4].upper()=='TEST':
        addBarcode(station,runid,barcode,action)
        return '', 200
      df = getBarcodeDF()
      if action=='input':
        if previous_station==barcode_stations_flow[0]:
          if checkPatientBarcode(barcode):
            addBarcode(station,runid,barcode,action)
            return '', 200
          else:
            return 'This barcodes does not exist: ' + barcode, 400
        else:
          if ((df['barcode']==barcode) & (df['station']==previous_station) & (df['action']=='output')).sum():
            if ((df['barcode']==barcode) & (df['station']==station) & (df['runid']!=runid) & (df['action']=='input')).sum():
              return 'Barcode already used for another Master Bath Record', 400
            else:
              addBarcode(station,runid,barcode,action)
              return '', 200
          else:
            return 'This barcode is not an output of a previous protocol', 400
      elif action=='output':
        if (df['barcode']==barcode).sum():
          if (df['barcode']==barcode).sum() == ((df['barcode']==barcode) & (df['runid']==runid) & (df['station']==station) & (df['action']=='output')).sum():
            return '', 200
          else:
            return 'Barcode already used for another Master Bath Record', 400
        else:
          addBarcode(station,runid,barcode,action)
          return '', 200
      else:
        return 'Wrong barcode type', 400

    def traceabilityMatrix(pcr_run_id = None):
      df = getBarcodeDF()
      if pcr_run_id is not None:
        df = df[(df['station']!='PCR') | (df['runid']==pcr_run_id)]
      start = 1
      for i, station in enumerate(barcode_stations_flow[start:-1]):
        partial_input = df[['barcode','runid']][(df['station']==station) & (df['action']=='input') ].copy()
        partial_output = df[['barcode','runid']][(df['station']==station) & (df['action']=='output') ].copy()
        partial = partial_input.merge(partial_output,on='runid',how='inner',suffixes=('_'+barcode_stations_flow[i+start],'_'+barcode_stations_flow[i+start+1])).drop('runid',axis=1)
        if i==0:
          result = partial.copy()
        else:
          result = result.merge(partial,on='barcode_'+barcode_stations_flow[i+start])
      pcr_barcode = df['barcode'][(df['station']=='PCR') & (df['action']=='input') ].copy()
      result = result[result['barcode_PCR'].isin(pcr_barcode)]
      def getPatientPosition(patientBarcode, barcodedf):
        runid = barcodedf[(barcodedf['barcode']==patientBarcode) & (barcodedf['station']=='station0')]['runid'].iloc[0]
        mbr_path = glob.glob('data/mbr/*/*{}.json'.format(runid))
        with open(mbr_path[0], 'r') as f:
          mbr = json.load(f)
        for idx,el in enumerate(mbr):
          if 'endpoint' in el:
            if ('input' in el['endpoint']) and el['result'] == patientBarcode:
              break
        return mbr[idx]['rackPosition']
      result['rack_position'] = result['barcode_station0'].apply(lambda x : getPatientPosition(str(x), df))
      def getRackNumber(rackBarcode, barcodedf):
        runid = barcodedf[(barcodedf['barcode']==rackBarcode) & (barcodedf['station']=='stationA')]['runid'].iloc[0]
        mbr_path = glob.glob('data/mbr/*/*{}.json'.format(runid))
        with open(mbr_path[0], 'r') as f:
          mbr = json.load(f)
        for idx,el in enumerate(mbr):
          if 'endpoint' in el:
            if ('input' in el['endpoint']) and el['result'] == rackBarcode:
              break
        return int(mbr[idx]['name'][-1])
      result['rack_number'] = result['barcode_stationA'].apply(lambda x : getRackNumber(x, df))
      result = result.merge(mapping, on=['rack_number','rack_position'], how='inner')
      result.drop(columns=['is_pct','is_nec'], inplace=True)
      return result

    @app.route("/api/results", methods = ['GET'])
    @biotech
    def results():
      if request.method == 'GET':
        result = traceabilityMatrix()
        return json.dumps(result.to_dict(orient='records')),200, {'ContentType':'application/json'}
       
    @app.route("/api/results/<pcrbarcode>/<position>", methods = ['GET'])
    @biotech
    def getResult(pcrbarcode,position):
      if request.method == 'GET':
        mbr, idx, idx1 = getPCRResult(pcrbarcode,position)
        data_preamble = mbr[idx]['result'].copy()
        data_preamble['username'] = mbr[idx]['operator']
        data_preamble['runDate'] = mbr[idx]['timestamp'][:10]
        data_preamble['runTime'] = mbr[idx]['timestamp'][11:19]
        data_preamble['plateBarcode'] = pcrbarcode
        del data_preamble['Wells']
        del data_preamble['NEC_PCT_results']
        return json.dumps({
          "data_preamble": data_preamble
          ,"NEC PCT results":mbr[idx]['result']['NEC_PCT_results']
          ,"wells_data": mbr[idx]['result']['Wells'][idx1]}
          ), 200, {'ContentType':'application/json'}
    return app

if __name__ == '__main__':
    app = create_app()
    if 'flaskhost' in os.environ:
      localhost = os.environ['flaskhost']
      app.debug = False
    else:
      localhost = 'localhost'
      app.debug = True
    app.run(host=localhost, port=5000, threaded=True, use_reloader=False)