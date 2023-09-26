from flask import Flask, render_template, flash, redirect, url_for, session, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, Form, PasswordField, validators, IntegerField, SelectField, FileField
from passlib.hash import sha256_crypt
from datetime import datetime, timedelta
import os
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy import  CheckConstraint, or_
from PIL import Image
import base64
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum
from functools import wraps



UPLOAD_FOLDER = '/home/omer/Desktop/Kütüphane/static/profilphoto/'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'image', 'gıf'} 
app = Flask(__name__)
app.secret_key = 'kitaplık'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://omeryuca:4192@localhost/kitaplık'
db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def base64_encode(data):
    return base64.b64encode(data).decode('utf-8')

app.jinja_env.filters['base64_encode'] = base64_encode

class UserRoleEnum(Enum):
    uye = 'uye'
    yonetici = 'yonetici'
    admin = 'admin'

class UserRoles(db.Model):
    __tablename__ = 'userroles'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    role = db.Column(SQLAlchemyEnum(UserRoleEnum), nullable=False, default=UserRoleEnum.uye)

class Users(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False) 
    email = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(35), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(SQLAlchemyEnum(UserRoleEnum), nullable=False, default=UserRoleEnum.uye)

    @classmethod
    def find_by_username(cls, username):
        return cls.query.filter_by(username=username).first()

class Permissions(db.Model):
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(SQLAlchemyEnum(UserRoleEnum), nullable=False, unique=True)
    addbook = db.Column(db.Boolean, default=False) 
    editbook = db.Column(db.Boolean, default=False)  
    deletebook = db.Column(db.Boolean, default=False)  
    addmember = db.Column(db.Boolean, default=False)  
    editmembers = db.Column(db.Boolean, default=False)  
    deletemembers = db.Column(db.Boolean, default=False)  
    lendbook = db.Column(db.Boolean, default=False)
        
def kullanici_izin_kontrol(user_id, istenen_izin):
    kullanici = Users.query.get(user_id)

    if kullanici:
        rol = kullanici.role
        izinler = Permissions.query.filter_by(role=rol).first()

        if izinler:
            if istenen_izin == "addbook":
                return izinler.addbook
            elif istenen_izin == "editbook":
                return izinler.editbook
            elif istenen_izin == "deletebook":
                return izinler.deletebook
            elif istenen_izin == "addmember":
                return izinler.addmember
            elif istenen_izin == "editmembers":
                return izinler.editmembers
            elif istenen_izin == "deletemembers":
                return izinler.deletemembers
            elif istenen_izin == "lendbook":
                return izinler.lendbook

    return False


# Kayıt formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators=[validators.Length(min=4, max=25, message="İsim Soyisim 2 ila 45 karakter arasında olmalıdır.")])
    username = StringField("Kullanıcı Adı", validators=[validators.Length(min=5, max=25, message="Kullanıcı Adı 5 ila 25 karakter arasında olmalıdır.")])
    email = StringField("Email Adresi", validators=[validators.Email(message="Lütfen geçerli bir email adresi giriniz.")])
    password = PasswordField("Parola:", validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin"),
        validators.EqualTo(fieldname="confirm", message="Parola uyuşmuyor")])
    confirm = PasswordField("Parola Doğrula")
   

# Kitap Ekleme Formu
class AddbookForm(Form):
    bookname = StringField("Bookname", validators=[
        validators.Length(min=1, max=50, message="Kitap adı 1 ila 50 karakter arasında olmalıdır.")])

    author = StringField("Author", validators=[
        validators.Length(min=2, max=35, message="Yazar adı 2 ila 35 karakter arasında olmalıdır.")])

    page = IntegerField("Page", validators=[
        validators.NumberRange(min=0, max=2000, message="Sayfa sayısı 0 ile 2000 arasında bir sayı olmalıdır.")])

    isbn = StringField("ISBN", validators=[
        validators.Regexp(r'^\d{13}$', message="Geçerli bir 13 haneli ISBN giriniz.")])
    
    date_published = StringField("Date", validators=[
        validators.Regexp(r'^\d{4}-\d{2}-\d{2}$', message="Geçerli bir tarih formatı giriniz.")])
    
    year_of_edition = IntegerField("Year", validators=[
        validators.NumberRange(min=0, max=2024, message="Yıl 0 ile 2024 arasında bir sayı olmalıdır.")])
    
    username = StringField("Username")
    
    def __init__(self, *args, **kwargs):
        super(AddbookForm, self).__init__(*args, **kwargs)
        self.date_published.data = datetime.now().strftime('%Y-%m-%d')  # Şu anki tarihi ayarla
        self.username.data = session.get('username')  # Oturumdan kullanıcı adını al

# Giriş formu
class LoginForm(Form):
    username = StringField("Kullanıcı Adı", validators=[validators.Length(min=5, max=25,message="Geçerli bir kullanıcı adı giriniz.")])
    password = PasswordField("Parola")

# Ana sayfa
@app.route("/")
def index():
    return render_template("index.html")

# Hakkında sayfası
@app.route("/about")
def about():
    return render_template("about.html")

# Kitapları gösterme sayfası
@app.route("/showbook")
def showbook():
    return render_template("showbook.html")

# Kitap Ekleme sayfası
@app.route("/addbook", methods=["GET", "POST"])
def addbook():
     user_id = session.get('user_id')
     istenen_izin = "addbook"

     if kullanici_izin_kontrol(user_id, istenen_izin) == False:
        flash("Bu işlemi yapmaya yetkiniz yok.", "danger")
        return redirect(url_for("booklist"))
     
     form = AddbookForm(request.form)

     if request.method == "POST" and form.validate():
        bookname = form.bookname.data.upper()
        author = form.author.data.upper()
        page = form.page.data
        isbn = form.isbn.data
        date_published = datetime.now().strftime('%Y-%m-%d')
        year_of_edition = form.year_of_edition.data
        username = session.get('username')
        new_book = Book(bookname=bookname, author=author, page=page, isbn=isbn, date_published=date_published, year_of_edition=year_of_edition, username=username)
        db.session.add(new_book)
        db.session.commit()

        flash("Başarıyla Kitap Eklendi.", "success")

        return redirect(url_for("index"))

     return render_template("addbook.html", form=form)

class EditbookForm(Form):
    id = IntegerField("Kitap ID", render_kw={"readonly": True})  # Kitap ID'sini görüntüle, değiştirilemez

    bookname = StringField("Bookname", validators=[
        validators.Length(min=1, max=50, message="Kitap adı 1 ila 50 karakter arasında olmalıdır.")])

    author = StringField("Author", validators=[
        validators.Length(min=2, max=35, message="Yazar adı 2 ila 35 karakter arasında olmalıdır.")])

    page = IntegerField("Page", validators=[
        validators.NumberRange(min=0, max=2000, message="Sayfa sayısı 0 ile 2000 arasında bir sayı olmalıdır.")])

    isbn = StringField("ISBN", validators=[
        validators.Regexp(r'^\d{13}$', message="Geçerli bir 13 haneli ISBN giriniz.")])

    date_published = StringField("Date", validators=[
        validators.Regexp(r'^\d{4}-\d{2}-\d{2}$', message="Geçerli bir tarih formatı giriniz.")])

    year_of_edition = IntegerField("Year", validators=[
        validators.NumberRange(min=0, max=2100, message="Yıl 0 ile 2100 arasında bir sayı olmalıdır.")])

    username = StringField("Username")

    def __init__(self, *args, **kwargs):
        super(EditbookForm, self).__init__(*args, **kwargs)
        self.date_published.data = datetime.now().strftime('%Y-%m-%d')  # Şu anki tarihi ayarla
        self.username.data = session.get('username')  # Oturumdan kullanıcı adını al

    def update_book(self, book):
        # Kitap bilgilerini güncelle
        book.bookname = self.bookname.data
        book.author = self.author.data
        book.page = self.page.data
        book.isbn = self.isbn.data
        book.date_published = self.date_published.data.strftime('%Y-%m-%d')
        book.year_of_edition = self.year_of_edition.data
        book.username = self.username.data
    

@app.route("/editbook/<int:id>", methods=["GET", "POST"])
def editbook(id):
    user_id = session.get('user_id')
    istenen_izin = "editbook"

    if kullanici_izin_kontrol(user_id, istenen_izin) == False:
        flash("Bu işlemi yapmaya yetkiniz yok.", "danger")
        return redirect(url_for("booklist"))

    form = EditbookForm(request.form)
    book = Book.query.get(id)

    if request.method == "POST" and form.validate():
        # Form verilerini kitap nesnesine kopyala
        form.populate_obj(book)

        # "id" sütununu güncelleme, otomatik artan olduğu için dokunma
        db.session.commit()

        flash("Kitap başarıyla güncellendi.", "success")
        return redirect(url_for("index"))

    # Form alanlarını doldur
    form.id.data = book.id
    form.bookname.data = book.bookname
    form.author.data = book.author
    form.page.data = book.page
    form.isbn.data = book.isbn
    form.date_published.data = book.date_published
    form.year_of_edition.data = book.year_of_edition
    form.username.data = book.username

    return render_template("editbook.html", form=form, book=book)

# Kayıt işlemi
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        new_user = Users(name=name, email=email, username=username, password=password, role='uye')
        db.session.add(new_user)
        db.session.commit()

        flash("Başarıyla Kayıt Oldunuz. Giriş Yapabilirsiniz.", "success")

        return redirect(url_for("login"))

    return render_template("register.html", form=form)

# Giriş işlemi
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    

    if request.method == "POST" and form.validate():
        username = form.username.data
        password_entered = form.password.data
        user = Users.find_by_username(username)

        if user:
            # Parola karşılaştırma
            if sha256_crypt.verify(password_entered, user.password):
                flash(f"Başarıyla giriş yaptın {username} .", "success")

                # Giriş başarılı
                session["Logged_in"] = True
                session["username"] = username
                session["user_id"] = user.id
                

                return redirect(url_for("index"))
            else:
                flash("Parola Yanlış. Lütfen Tekrar deneyin.", "danger")
        else:
            flash("Böyle Bir Kullanıcı Bulunamadı.", "danger")

    return render_template("login.html", form=form)
# Çıkış işlemi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

#Kitap Listesi
class Book(db.Model):
    __tablename__ = 'book'

    id = db.Column(db.Integer, primary_key=True)
    bookname = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    page = db.Column(db.Integer, nullable=False)
    isbn = db.Column(db.String(13), nullable=False)  
    date_published = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD formatında
    year_of_edition = db.Column(db.Integer, nullable=False)  # Yıl 
    username = db.Column(db.String(255), nullable=False)
    given_member = db.Column(db.String(255), nullable=False)
    end_date = db.Column(db.String(10), nullable=False)
    remaining_day = db.Column(db.Integer, nullable=False)

    def give_member(self, given_member):
        # Mevcut verilen üyeleri ayırın
        given_members = self.given_member.split(",") if self.given_member else []

        # Yeni üyeyi ekle
        given_members.append(given_member)

        # Yeni verilen üyeleri birleştirin ve veritabanına kaydedin
        self.given_member = ",".join(given_members)

class Contact(db.Model):
    __tablename__ = 'contact'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(11), nullable=False)
    message = db.Column(db.String(1000), nullable=False)  

class ContactForm(Form):
    name = StringField("İsim Soyisim", validators=[validators.length(min=2, max=45, message="İsim Soyisim 2 ila 45 karakter arasında olmalıdır.")])
    email = StringField("Email Adresi", validators=[validators.Email(message="Lütfen geçerli bir email adresi giriniz.")])
    phone_number =StringField("Phone Number", validators=[
        validators.Regexp(r'^\d{11}$', message="Geçerli bir 11 haneli telefon numarası giriniz. Örn: 01234567890")])
    message = StringField("Message", validators=[validators.length(min=30, max=3000, message="Minimum 30 karakter maksimum 3000 karakter bir mesaj iletiniz.")])

#iletişim sayfası
@app.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm(request.form)


    if request.method == "POST" and form.validate():
        name = form.name.data
        email = form.email.data
        phone_number = form.phone_number.data
        message = form.message.data

        new_contact = Contact(name=name, email=email, phone_number=phone_number, message=message)
        db.session.add(new_contact)
        db.session.commit()

        flash("Mesajınız bize ulaştı. Düşünceniz için teşekkür ederiz", "success")

        return redirect(url_for("index"))

    return render_template("contact.html", form=form)

@app.route("/booklist")
def booklist():
    books = Book.query.all()
    for book in books:
        if book.end_date:
            end_date = datetime.strptime(book.end_date, '%Y-%m-%d').date()
            remaining_days = (end_date - datetime.now().date()).days
            book.remaining_day = remaining_days

    db.session.commit()


    return render_template("booklist.html", books=books)



@app.route("/deletebook/<int:id>", methods=["GET", "POST"])
def deletebook(id):
    user_id = session.get('user_id')
    istenen_izin = "deletebook"

    if kullanici_izin_kontrol(user_id, istenen_izin) == False:
        flash("Bu işlemi yapmaya yetkiniz yok.", "danger")
        return redirect(url_for("booklist"))
    book = Book.query.get(id)  

    if book:
        db.session.delete(book)  
        db.session.commit()
        flash("Kitap başarıyla silindi.", "success")
    else:
        flash("Böyle bir kitap bulunamadı.", "danger")

    return redirect(url_for("booklist")) 

class Member(db.Model):
    __tablename__ = 'member'
 
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phonenumber = db.Column(db.String(11), nullable=False)
    lendbook = db.Column(db.String(255), unique=True, nullable=False)
    date_given = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD formatında
    photo = db.Column(db.String(255), nullable=True)
    image = db.Column(BYTEA, nullable=True)
    imag = db.Column(db.String(255))


    def lend_book(self, book_id, book_name):
        # lendbook sütununa kitap ID'si ve adını birleştirerek ekleyin
        if self.lendbook:
            self.lendbook += f",{book_id}-{book_name}"
        else:
            self.lendbook = f"{book_id}-{book_name}"

        # date_given sütununu güncel tarihe ayarlayın
        self.date_given = datetime.now().strftime('%Y-%m-%d')

    def save_photo(self, photo_data):
        self.photo = photo_data
        db.session.commit()


@app.route("/memberlist")
def memberlist():
    members = Member.query.all()
    return render_template("memberlist.html", members=members)

class AddmemberForm(Form):
    name = StringField("Name", validators=[
        validators.Length(min=1, max=50, message="Name 1 ila 50 karakter arasında olmalıdır.")])

    age = IntegerField("Age", validators=[
        validators.NumberRange(min=0, max=99, message="Age 0 ile 99 arasında bir sayı olmalıdır.")])

    email = StringField("Email Adresi", validators=[validators.Email(message="Lütfen geçerli bir email adresi giriniz.")])

    phonenumber =StringField("Phone Number", validators=[
        validators.Regexp(r'^\d{11}$', message="Geçerli bir 11 haneli telefon numarası giriniz. Örn: 01234567890")])
    
@app.route("/addmember", methods=["GET", "POST"])
def addmember():
    user_id = session.get('user_id')
    istenen_izin = "addmember"

    if kullanici_izin_kontrol(user_id, istenen_izin) == False:
        flash("Bu işlemi yapmaya yetkiniz yok.", "danger")
        return redirect(url_for("memberlist"))
    form = AddmemberForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data.upper()
        age= form.age.data
        email = form.email.data
        phonenumber = form.phonenumber.data.upper()

        new_member = Member(name=name, email=email, age=age, phonenumber=phonenumber)
        db.session.add(new_member)
        db.session.commit()

        flash("Başarıyla Üye Eklediniz.", "success")

        return redirect(url_for("memberlist"))

    return render_template("addmember.html", form=form)

class EditmemberForm(Form):
    id = IntegerField("ID", render_kw={"readonly": True})

    name = StringField("Name", validators=[
        validators.Length(min=1, max=50, message="Name 1 ila 50 karakter arasında olmalıdır.")])

    age = IntegerField("Age", validators=[
        validators.NumberRange(min=0, max=99, message="Age 0 ile 99 arasında bir sayı olmalıdır.")])

    email = StringField("Email Adresi", validators=[validators.Email(message="Lütfen geçerli bir email adresi giriniz.")])

    phonenumber =StringField("Phone Number", validators=[
        validators.Regexp(r'^\d{11}$', message="Geçerli bir 11 haneli telefon numarası giriniz. Örn: 01234567890")])    

    def __init__(self, *args, **kwargs):
        super(EditmemberForm, self).__init__(*args, **kwargs)

    def update_member(self, member):
        member.name = self.name.data.upper()
        member.age = self.age.data
        member.email = self.email.data.upper()
        member.phonenumber = self.phonenumber.data.upper()
    

@app.route("/editmembers/<int:id>", methods=["GET", "POST"])
def editmember(id):
    user_id = session.get('user_id')
    istenen_izin = "editmembers"

    if kullanici_izin_kontrol(user_id, istenen_izin) == False:
        flash("Bu işlemi yapmaya yetkiniz yok.", "danger")
        return redirect(url_for("memberlist"))
    form = EditmemberForm(request.form)
    member = Member.query.get(id)

    if request.method == "POST" and form.validate():
        # Form verilerini kitap nesnesine kopyala
        form.populate_obj(member)
        db.session.commit()

        flash("Üye başarıyla güncellendi.", "success")
        return redirect(url_for("index"))

    # Form alanlarını doldur
    form.id.data = member.id
    form.name.data = member.name.upper()
    form.age.data = member.age
    form.email.data = member.email
    form.phonenumber.data = member.phonenumber.upper()


    return render_template("editmembers.html", form=form, member=member)

@app.route("/deletemembers/<int:id>", methods=["GET", "POST"])
def deletemember(id):
    user_id = session.get('user_id')
    istenen_izin = "deletemembers"

    if kullanici_izin_kontrol(user_id, istenen_izin) == False:
        flash("Bu işlemi yapmaya yetkiniz yok.", "danger")
        return redirect(url_for("memberlist"))
    member = Member.query.get(id)  # Silinecek kitabı veritabanından al
    
    if member:
        db.session.delete(member)  # Kitabı veritabanından sil
        db.session.commit()
        flash("Üye başarıyla silindi.", "success")
    else:
        flash("Böyle bir üye bulunamadı.", "danger")

    return redirect(url_for("memberlist")) 

class PhotomemberForm(Form):
    id = IntegerField("ID", render_kw={"readonly": True})

    name = StringField("Name", render_kw={"readonly": True})
        


class LendbookForm(Form):
    id = IntegerField("Kitap ID", render_kw={"readonly": True})  

    bookname = StringField("Bookname", validators=[
        validators.Length(min=1, max=50, message="Kitap adı 1 ila 50 karakter arasında olmalıdır.")])

    author = StringField("Author", validators=[
        validators.Length(min=2, max=35, message="Yazar adı 2 ila 35 karakter arasında olmalıdır.")])
    
    name = SelectField("İsim Soyisim", coerce=str)

    def __init__(self, *args, **kwargs):
        super(LendbookForm, self).__init__(*args, **kwargs)

@app.route("/lendbook/<int:id>", methods=["GET", "POST"])
def lendbook(id):
    user_id = session.get('user_id')
    istenen_izin = "lendbook"

    if kullanici_izin_kontrol(user_id, istenen_izin) == False:
        flash("Bu işlemi yapmaya yetkiniz yok.", "danger")
        return redirect(url_for("booklist"))
    
    form = LendbookForm(request.form)
    book = Book.query.get(id)
    members = Member.query.all()
    form.name.choices = [(member.id, member.name) for member in members]
    
    if request.method == "POST" and form.validate():
        
        selected_member = Member.query.get(form.name.data)
        selected_member.lend_book(book.id, book.bookname)
        book.give_member(selected_member.name)
        current_date = datetime.now()
        end_date = current_date + timedelta(days=15)
        book.end_date = end_date.strftime('%Y-%m-%d')

        db.session.commit()
        
        flash(f"Kitap başarıyla {selected_member.name} üyemize verildi.", "success")
        return redirect(url_for("index"))

    # Form alanlarını doldur
    form.id.data = book.id
    form.bookname.data = book.bookname
    form.author.data = book.author


    return render_template("lendbook.html", form=form, book=book)

@app.route("/upload_photo/<int:id>", methods=["GET","POST"])
def upload_file(id):
    form = PhotomemberForm(request.form)
    member = Member.query.get(id)

    if request.method == 'POST':
        file = request.files['file']

        if file and allowed_file(file.filename):
            image_data = base64.b64encode(file.read()).decode('utf-8')  # Dosyayı base64 ile kodla
            member.image = image_data  # Veritabanında metin olarak sakla
            db.session.commit()

            flash('Profil Fotoğrafınız Güncellendi', 'success')
            
        else:
            flash('Geçersiz dosya türü', 'danger')

    form.id.data = member.id
    form.name.data = member.name

    return render_template("/upload_photo.html", form=form, member=member)


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("login"))
    else:
        keyword = request.form.get("keyword")

        members = Member.query.filter(
            or_(
                Member.name.ilike(f"%{keyword}%"),
                Member.email.ilike(f"%{keyword}%"),
                Member.phonenumber.ilike(f"%{keyword}%"),
                Member.lendbook.ilike(f"%{keyword}%") # type: ignore
            )
        ).all()

        if not members:
            flash("Aranan kelimeye uygun üye bulunamadı...", "warning")
            return redirect(url_for("memberlist"))
        else:
            return render_template("memberlist.html", members=members)

@app.route("/searchbook", methods=["GET", "POST"])
def ara():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
       
        books = Book.query.filter(
            or_(
                Book.bookname.ilike(f"%{keyword}%"),
                Book.author.ilike(f"%{keyword}%")
            )
        ).all()

        if not books:
            flash("Aranan kelimeye uygun kirap bulunamadı...", "warning")
            return redirect(url_for("booklist"))
        else:
            return render_template("booklist.html", books=books)

@app.route("/kontrolpaneli" , methods=["GET", "POST"])
def kontrolpaneli():
    if request.method == "POST":
        # Formdan gelen verileri işleyin ve veritabanında güncelleyin
        for permission in Permissions.query.all():
            permission.addbook = bool(request.form.get(f"addbook_{permission.id}"))
            permission.editbook = bool(request.form.get(f"editbook_{permission.id}"))
            permission.deletebook = bool(request.form.get(f"deletebook_{permission.id}"))
            permission.addmember = bool(request.form.get(f"addmember_{permission.id}"))
            permission.editmembers = bool(request.form.get(f"editmembers_{permission.id}"))
            permission.deletemembers = bool(request.form.get(f"deletemembers_{permission.id}"))
            permission.lendbook = bool(request.form.get(f"lendbook_{permission.id}"))
        
        for user in UserRoles.query.all():
            user_role = request.form.get(f"user_role_{user.user_id}")
            user.role = user_role

        # Değişiklikleri veritabanına kaydedin
        db.session.commit()
        
        flash("İzinler ve kullanıcı rolleri başarıyla güncellendi.", "success")
        return redirect(url_for("kontrolpaneli"))

    # Eğer GET isteği yapılırsa, mevcut izinleri ve kullanıcıları alın ve kontrol panelini gösterin
    permissions = Permissions.query.all()
    users = Users.query.all()
    return render_template("kontrolpaneli.html", permissions=permissions, users=users)



@app.route('/update_permissions', methods=['POST'])
def update_permissions():
    if request.method == 'POST':
        # Formdan gelen verileri işle
        permission_updates = request.form.to_dict()

        for permission_id, updates in permission_updates.items():
            # İzin ID'sini çıkar
            permission_id = permission_id.split('_')[-1]

            # Veritabanında izni bul
            permission = Permissions.query.get(permission_id)

            if permission:
                # İzin güncelleme verilerini al
                addbook_permission = request.form.get(f'addbook_{permission_id}') == 'True'
                editbook_permission = request.form.get(f'editbook_{permission_id}') == 'True'
                deletebook_permission = request.form.get(f'deletebook_{permission_id}') == 'True'
                addmember_permission = request.form.get(f'addmember_{permission_id}') == 'True'
                editmembers_permission = request.form.get(f'editmembers_{permission_id}') == 'True'
                deletemembers_permission = request.form.get(f'deletemembers_{permission_id}') == 'True'
                lendbook_permission = request.form.get(f'lendbook_{permission_id}') == 'True'

                # İzni güncelle
                permission.addbook = addbook_permission
                permission.editbook = editbook_permission
                permission.deletebook = deletebook_permission
                permission.addmember = addmember_permission
                permission.editmembers = editmembers_permission
                permission.deletemembers = deletemembers_permission
                permission.lendbook = lendbook_permission

                # Veritabanındaki değişiklikleri kaydet
                db.session.commit()

        flash("İzinler başarıyla güncellendi.", "success")

    # İzin güncelleme işlemi tamamlandıktan sonra bir sayfaya yönlendirin
    return redirect(url_for('index'))

@app.route('/update_users', methods=['POST'])
def update_users():
    if request.method == 'POST':
        # Formdan gelen verileri işle
        user_updates = request.form.to_dict()

        for user_id, updates in user_updates.items():
            # Kullanıcı ID'sini çıkar
            user_id = user_id.split('_')[-1]

            # Veritabanında kullanıcıyı bul
            user = Users.query.get(user_id)

            if user:
                # Kullanıcı rolünü güncelle
                user.role = request.form.get(f'user_role_{user_id}')

                # Veritabanındaki değişiklikleri kaydet
                db.session.commit()

        flash("Kullanıcı rolleri başarıyla güncellendi.", "success")

    # Rollerin güncellenmesi işlemi tamamlandıktan sonra bir sayfaya yönlendirin
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
