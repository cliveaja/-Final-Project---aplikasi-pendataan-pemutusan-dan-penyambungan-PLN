from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, Response, json, session
from flaskext.mysql import MySQL
from wtforms import Form, StringField, TextField, TextAreaField, PasswordField, validators, IntegerField, FileField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict
from twilio.rest import Client
import flask_excel as excel
import csv
import jwt
from os import path, getcwd
from functools import wraps
from flask_cors import CORS
import base64
import re
import gammu
import sys

app = Flask(__name__)
cors = CORS(app, origins=["*"])

mysql = MySQL()

app.config['static'] = path.join(getcwd(), 'static')


# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'tusbung'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

account_sid = "AC5435f395088aeeffced12d434c36b901"
auth_token = "0c969a035bfe6cf95ef07b6910e9329e"

# --SUCCESS FUNCTION HANDLING
def success_handle(output, status=200, mimetype='application/json'):
    return Response(output, status=status, mimetype=mimetype)

# --ERROR FUNCTION HANDLING-- #
def error_handle(error_message, status=500, mimetype='application/json'):
    return Response(json.dumps({"error": {"message": error_message}}), status=status, mimetype=mimetype)

def get_petugas_id(petugas_id):
    petugas = {}
    conn = mysql.connect()
    cursor = conn.cursor()
    query = "SELECT * FROM petugas"
    cursor.execute(query)
        
    for row in query:
        petugas = {
            "id_petugas": row[1],
            "nama": row[2],
            "alamat": row[3],
            "status": row[4],
            "telpon": row[5],
        }
    if 'id' in petugas:
        return petugas
    return None

# --FUNCTION DELETE USER-- #
def hpspetugas(petugas_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    query = "DELETE FROM petugas WHERE id_petugas=%s"
    cursor.execute(query, petugas_id)
    conn.commit()

    return query

def hpspemutusan():
    conn = mysql.connect()
    cursor = conn.cursor()
    query = "TRUNCATE TABLE data_pemutusan"
    cursor.execute(query)
    conn.commit()

    return query

def hpspenyambungan():
    conn = mysql.connect()
    cursor = conn.cursor()
    query = "TRUNCATE TABLE data_penyambungan"
    cursor.execute(query)
    conn.commit()

    return query


@app.route("/", methods=['POST', 'GET'])
#  Login untuk web
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # masukkan ke database
        conn = mysql.connect()
        cursor = conn.cursor()
        query = "SELECT * FROM user"
        cursor.execute(query)
        result = cursor.fetchone()

        if result[1] == username and result[2] == password:
            session['logged_in'] = True
            session['username'] = username
            flash('You are now logged in', 'success')
            return render_template("kirimPesan.html")
        else:
            error = 'Invalid Name or Password'
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# --CEK AUTENTIKASI SEBELUM MASUK URL LAIN-- #
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please Login!', 'danger') # pesan jika tidak ada autentikasi masuk
            return redirect(url_for('login'))
    return wrap

@app.route("/kirimPesan", methods=['GET', 'POST'])
def kirimPesan():
    if request.method == "GET":
        return render_template("kirimPesan.html")
    else:
        pesan = request.form['pesan']
        nomor = request.form['nomor']

        client = Client(account_sid, auth_token)
        client.messages.create(
            to=nomor,
            from_="+19292039756",
            body=pesan
        )
        flash("Pesan terkirim", "success")
        return render_template("kirimPesan.html")

@app.route("/viewkaryawan", methods=['GET'])
@is_logged_in
def viewKar():
    conn = mysql.connect()
    cursor = conn.cursor()
    query = "SELECT * FROM petugas"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    # conn.commit()
    return render_template('viewKaryawan.html', view=results)

# class TambahPetugasForm(Form):
#     id = StringField('Id', [validators.Length(min=1, max=50)])
#     nama = StringField('Nama', [validators.Length(min=1, max=50)])
#     alamat = StringField('Alamat', [validators.Length(min=1, max=50)])
#     telpon = IntegerField('Telpon', [validators.required('Number Only')])
#     password = StringField('Password', [validators.Length(min=1, max=50)])

@app.route("/tambahPetugas", methods=['GET', 'POST'])
@is_logged_in
def tkaryawan():
    if request.method == 'POST':
        petugas_id = request.form['id']
        nama = request.form['nama']
        alamat = request.form['alamat']
        telpon = request.form['telpon']
        password = request.form['password']
        status = request.form.get('status')
        rbm = request.form.get('rbm')

        conn = mysql.connect()
        cursor = conn.cursor()
        query = "INSERT INTO petugas(id_petugas, nama, alamat, status, telpon, password, rbm) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        value = (petugas_id, nama, alamat, status, telpon, password, rbm)
        cursor.execute(query, value)
        conn.commit()
        return redirect(url_for("viewKar"))
    else:
        return render_template('tambahPetugas.html', status=[{'status':'Menikah'},{'status':'Belum Menikah'}], datarbm=[{'datarbm':'103116'},{'datarbm':'103117'},{'datarbm':'103118'},{'datarbm':'103119'},{'datarbm':'103120'}])
    

class EditPetugasForm(Form):
    nama = StringField('Nama', [validators.Length(min=1, max=50)])
    alamat = StringField('Alamat', [validators.Length(min=1, max=50)])
    status = StringField('Status', [validators.Length(min=1, max=50)])
    telpon = IntegerField('Telpon', [validators.required('Number Only')])
    password = StringField('Password', [validators.Length(min=1, max=50)])

@app.route("/editPetugas/<int:petugas_id>", methods=['POST', 'GET'])
def edit_Petugas(petugas_id):
    form = EditPetugasForm(request.form)    
    if request.method == 'POST' and form.validate():
        nama = request.form['nama']
        alamat = request.form['alamat']
        status = request.form['status']
        telpon = request.form['telpon']
        rbm = request.form['rbm']
        password = request.form['password']
        conn2 = mysql.connect()
        cursor2 = conn2.cursor()
        query2 = "UPDATE petugas SET nama=%s, alamat=%s, status=%s, telpon=%s, password=%s, rbm=%s WHERE id_petugas=%s"
        value = (nama, alamat, status, telpon, password, rbm, petugas_id)
        cursor2.execute(query2, value)
        conn2.commit()
        print(query2)

        flash('data berhasil diubah', 'success')
        return redirect(url_for('viewKar'))
    else:
        conn = mysql.connect()
        cursor = conn.cursor()
        query = "SELECT * FROM petugas WHERE id_petugas=%s"
        cursor.execute(query, petugas_id)
        results1 = cursor.fetchone()
        cursor.close()

        form.nama.data = results1[2]
        form.alamat.data = results1[3]
        form.status.data = results1[4]
        form.telpon.data = results1[5]
        form.password.data = results1[7]

        return render_template('editPetugas.html', form=form, result=results1, datarbm=[{'rbm':'103116'},{'rbm':'103117'},{'rbm':'103118'},{'rbm':'103119'},{'rbm':'103120'}], datastatus=[{'status':'Menikah'},{'status':'Belum Menikah'}])

# --HAPUS KARYAWAN-- #
@app.route('/hapus_petugas/<int:petugas_id>', methods=['GET', 'DELETE', 'POST'])
@is_logged_in
def hapusPetugas(petugas_id):
    if request.method == 'POST':
        hpspetugas(petugas_id)
        return redirect(url_for("viewKar"))
    return render_template("viewKaryawan.html")

@app.route("/upload/pemutusan", methods=['GET', 'POST'])
@is_logged_in
def pemutusan():
    if request.method == 'POST':
        file = request.files['file']
        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file, delimiter=",")
        data = [row for row in reader]
        for row in data:
            conn = mysql.connect()
            cursor = conn.cursor()
            query = "INSERT INTO data_pemutusan(id_pelanggan, nama, alamat, tarif, daya, rbm, langkah, lembar, tagihan) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            value = (row['ID PELANGGAN'], row['NAMA'], row['ALAMAT'], row['TARIF'], row['DAYA'], row['RBM'], row['LANGKAH'], row['LEMBAR'], row['TAGIHAN'])
            cursor.execute(query, value)
            conn.commit()
    conn = mysql.connect()
    cursor1 = conn.cursor()
    cursor2 = conn.cursor()
    query = "SELECT * FROM data_pemutusan ORDER BY status DESC"
    queryListPetugas = "SELECT * FROM petugas"
    cursor1.execute(query)
    cursor2.execute(queryListPetugas)
    results = cursor1.fetchall()
    listPetugas = cursor2.fetchall()
    cursor1.close()
    cursor2.close()

    j = 0
    if len(results) != 0:
        for i in results:
            if i[11] == "":
                continue
            j += 1

    return render_template('pemutusan.html', views=results, eksekusi=j, datapetugas=listPetugas, data=[{'area':'Nagoya'},{'area':'Batam Centre'},{'area':'Batu Aji'},{'area':'Tiban'}])

@app.route('/hapusPemutusan', methods=['GET', 'DELETE', 'POST'])
@is_logged_in
def hapusDataPemutusan():
    if request.method == 'POST':
        hpspemutusan()
        flash('data berhasil dihapus', 'success')
        return redirect(url_for("pemutusan"))
    return render_template("pemutusan.html")

@app.route("/upload/penyambungan", methods=['GET', 'POST'])
@is_logged_in
def penyambungan():
    if request.method == 'POST':
        file = request.files['file']
        # area = request.form.get('area')
        # petugasId = request.form['petugas']
        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file, delimiter=",")
        data = [row for row in reader]
        for row in data:
            conn = mysql.connect()
            cursor = conn.cursor()
            query = "INSERT INTO data_penyambungan(id_pelanggan, nama, alamat, tarif, daya, telpon, rbm) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            value = (row['ID PELANGGAN'], row['NAMA'], row['ALAMAT'], row['TARIF'], row['DAYA'], row['No HP'], row['RBM'])
            cursor.execute(query, value)
            conn.commit()
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor2 = conn.cursor()
    query = "SELECT * FROM data_penyambungan ORDER BY status DESC"
    queryListPetugas = "SELECT * FROM petugas"
    cursor.execute(query)
    cursor2.execute(queryListPetugas)
    results = cursor.fetchall()
    listPetugas = cursor2.fetchall()
    cursor.close()
    cursor2.close()

    j = 0
    if len(results) != 0:
        for i in results:
            if i[8] == "":
                continue
            j += 1

    return render_template('penyambungan.html', eksekusi=j, views=results, petugas=listPetugas, data=[{'area':'Nagoya'},{'area':'Batam Centre'},{'area':'Batu Aji'},{'area':'Tiban'}])

@app.route('/hapusPenyambungan', methods=['GET', 'DELETE', 'POST'])
@is_logged_in
def hapusDataPenyambungan():
    if request.method == 'POST':
        hpspenyambungan()
        flash('data berhasil dihapus', 'success')
        return redirect(url_for("penyambungan"))
    return render_template("penyambungan.html")

@app.route("/listPetugas", methods=['GET'])
@is_logged_in
def list_petugas():
    area = request.args.get('area', type = str)
    conn = mysql.connect()
    cursor = conn.cursor()
    query = "SELECT * FROM petugas WHERE area IN (%s)"
    cursor.execute(query, area)
    results = cursor.fetchall()
    cursor.close()
    
    return json.dumps(results)


# @app.route("/export", methods=['GET'])
# def export_records():
#     return excel.make_response_from_array([[1,2], [3, 4]], "csv",
#                                           file_name="export_data")

#------------------------------------------------------------------------
    # API for Mobile App (Petugas)
#------------------------------------------------------------------------

def data_penyambungan(petugas_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursorPlgn = conn.cursor()
    queryPelanggan = "SELECT * FROM petugas WHERE id_petugas=%s"
    query = "SELECT * FROM data_penyambungan WHERE rbm=%s AND status=''"
    cursorPlgn.execute(queryPelanggan, petugas_id)
    pelangganData = cursorPlgn.fetchone()
    cursor.execute(query, pelangganData[9])
    result = cursor.fetchall()
    return result

def laporan_penyambungan(petugas_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursorPlgn = conn.cursor()
    queryPelanggan = "SELECT * FROM petugas WHERE id_petugas=%s"
    query = "SELECT * FROM data_penyambungan WHERE rbm=%s AND status='true'"
    cursorPlgn.execute(queryPelanggan, petugas_id)
    pelangganData = cursorPlgn.fetchone()
    cursor.execute(query, pelangganData[9])
    result = cursor.fetchall()
    return result

def data_pemutusan(petugas_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursorPlgn = conn.cursor()
    queryPelanggan = "SELECT * FROM petugas WHERE id_petugas=%s"
    query = "SELECT * FROM data_pemutusan WHERE rbm=%s AND status='' ORDER BY nama ASC"
    cursorPlgn.execute(queryPelanggan, petugas_id)
    pelangganData = cursorPlgn.fetchone()
    cursor.execute(query, pelangganData[9])
    result = cursor.fetchall()
    return result

def laporan_pemutusan(petugas_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    cursorPlgn = conn.cursor()
    queryPelanggan = "SELECT * FROM petugas WHERE id_petugas=%s"
    query = "SELECT * FROM data_pemutusan WHERE rbm=%s AND status='true'"
    cursorPlgn.execute(queryPelanggan, petugas_id)
    pelangganData = cursorPlgn.fetchone()
    cursor.execute(query, pelangganData[9])
    result = cursor.fetchall()
    return result

def data_id_pelanggan(id_pelanggan):
    conn = mysql.connect()
    cursor = conn.cursor()
    query = "SELECT * FROM data_penyambungan WHERE id_pelanggan=%s"
    cursor.execute(query, id_pelanggan)
    result = cursor.fetchone()

    return result

# Login untuk mobile
@app.route("/mobile/login", methods=['POST'])
def m_login():
    # get username & password
    data = json.loads(request.data)
    id_petugas = data['id_petugas']
    password = data['password']

    # query search for petugas
    conn = mysql.connect()
    cursor = conn.cursor()

    query = "SELECT * FROM petugas WHERE id_petugas=%s"
    cursor.execute(query, (id_petugas))
    result = cursor.fetchone()

    # kalau ketemu kirim token dalam bentuk object,
    # kalau tidak kirim pesan berbentuk object
    if result == None:
        res = { "success": False, "result": "ID Petugas tidak ditemukan" }
        return json.jsonify(res)

    if password != result[7]:
        res = { "success": False, "result": "Password salah" }
        return json.jsonify(res)
    encode_jwt = jwt.encode({'id_petugas': result[1]}, 'harahap', algorithm='HS256')
    res = { "success": True, "result": str(encode_jwt.decode('utf-8'))}
    return json.jsonify(res)

@app.route('/mobile/data/penyambungan/<int:petugas_id>', methods=['GET'])
def get_data_penyambungan(petugas_id):
    # query
    # SELECT * FROM penyambungan WHERE id_petugas=?
    data = data_penyambungan(petugas_id)
    return json.jsonify(data)

@app.route('/mobile/data/pemutusan/<int:petugas_id>', methods=['GET'])
def get_data_pemutusan(petugas_id):
    # query
    # SELECT * FROM pemutusan WHERE id_petugas=?
    data = data_pemutusan(petugas_id)
    return json.jsonify(data)

# update keterangan
@app.route('/mobile/data/penyambungan/update/<int:id_pelanggan>', methods=["POST"])
def update_data_penyambungan(id_pelanggan):
    data = json.loads(request.data)
    keterangan = data["keterangan"]
    status = data['status'] # [true, false]
    foto = data["foto"]
    imgstr = re.search(r'data:image/jpeg;base64,(.*)',foto).group(1)
    convert = open("static/foto/"+str(id_pelanggan)+".jpg", 'wb')
    decoded = base64.b64decode(imgstr)
    convert.write(decoded)
    convert.close()

    # query search for petugas
    conn = mysql.connect()
    cursor1 = conn.cursor()

    query1 = "UPDATE data_penyambungan SET keterangan=%s, status=%s, foto=%s WHERE id_pelanggan=%s"
    cursor1.execute(query1, (keterangan, status, "static/foto/"+str(id_pelanggan)+".jpg", id_pelanggan))
    conn.commit()

    res = { "success": True, "result": "Data berhasil diubah" }

    return json.jsonify(res)

# update keterangan
@app.route('/mobile/data/pemutusan/update/<int:id_pelanggan>', methods=["POST"])
def update_data_pemutusan(id_pelanggan):
    data = json.loads(request.data)
    keterangan = data["keterangan"]
    status = data['status'] # [true, false]
    foto = data["foto"]
    imgstr = re.search(r'data:image/jpeg;base64,(.*)',foto).group(1)
    convert = open("static/foto/"+str(id_pelanggan)+".jpg", 'wb')
    decoded = base64.b64decode(imgstr)
    convert.write(decoded)
    convert.close()

    # query search for petugas
    conn = mysql.connect()
    cursor1 = conn.cursor()

    query1 = "UPDATE data_pemutusan SET status=%s, keterangan=%s, foto=%s WHERE id_pelanggan=%s"
    cursor1.execute(query1, (status, keterangan, "static/foto/"+str(id_pelanggan)+".jpg", id_pelanggan))
    conn.commit()

    res = { "success": True, "result": "Data berhasil diubah" }

    return json.jsonify(res)

@app.route('/mobile/laporan/pemutusan/<int:petugas_id>', methods=["GET"])
def lap_pemutusan(petugas_id):
    data = laporan_pemutusan(petugas_id)
    return json.jsonify(data)

@app.route('/mobile/laporan/penyambungan/<int:petugas_id>', methods=['GET'])
def lap_penyambungan(petugas_id):
    data = laporan_penyambungan(petugas_id)
    return json.jsonify(data)








# @app.route('/mobile/data/pemutusan/update/<int:id_pelanggan>', methods=["POST"])
# def update_data_pemutusan(id_pelanggan):
#     data = json.loads(request.data)
#     keterangan = data["keterangan"]
#     status = data['status'] # [true, false]

#     # query search for petugas
#     conn = mysql.connect()
#     cursor1 = conn.cursor()

#     query1 = "UPDATE data_pemutusan SET keterangan=%s, status=%s WHERE id_pelanggan=%s"
#     cursor1.execute(query1, (keterangan, status, id_pelanggan))
#     conn.commit()

#     res = { "success": True, "result": "Data berhasil diubah" }

#     return json.jsonify(res)


if __name__ == '__main__':
    app.config['SECRET_KEY'] = 'rahasianih!'
    app.run(debug=True, host="192.168.43.94")