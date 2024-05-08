from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SelectField, IntegerField
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = '3.146.178.7'
app.config['MYSQL_USER'] = 'paolo'
app.config['MYSQL_PASSWORD'] = 'Paolo_Marcelo#11'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_DB'] = 'stocks'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('home.html')

#Products
@app.route('/products')
def products():
    cur=mysql.connection.cursor()
    result = cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    if result>0:
        return render_template('products.html', products = products)
    else:
        msg='Productos no hallados'
        return render_template('products.html', msg=msg)
    cur.close()

@app.route('/locations')
def locations():
    cur=mysql.connection.cursor()
    result = cur.execute("SELECT * FROM locations")

    locations = cur.fetchall()

    if result>0:
        return render_template('locations.html', locations = locations)
    else:
        msg='Ubicación no encontrada'
        return render_template('locations.html', msg=msg)
    cur.close()

@app.route('/product_movements')
def product_movements():
    #create cursor
    cur=mysql.connection.cursor()

    #Get products
    result = cur.execute("SELECT * FROM productmovements")

    movements = cur.fetchall()

    if result>0:
        return render_template('product_movements.html', movements = movements)
    else:
        msg='Movimiento de producto no encontrada'
        return render_template('product_movements.html', msg=msg)
    #close connection
    cur.close()

@app.route('/article/<string:id>/')
def article(id):
    cur=mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles WHERE id = %s",[id])

    article = cur.fetchone()
    return render_template('article.html', article = article)

class RegisterForm(Form):
    name = StringField('Nombre', [validators.Length(min=1, max=50)])
    username = StringField('Usuario', [validators.Length(min=1, max=25)])
    email = StringField('Correo', [validators.length(min=6, max=50)])
    password = PasswordField('Contraseña', [
        validators.DataRequired(),
        validators.EqualTo('confirmar', message='Contraseña incorrecta')
    ])
    confirm = PasswordField('Confirmar contraseña')

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()

        cur.execute("INSERT into users(name, email, username, password) VALUES(%s,%s,%s,%s)",(name, email, username, password))

        mysql.connection.commit()

        cur.close()

        flash("Registrado con exito", "Correcto")
        
        return redirect(url_for('login'))
    return render_template('register.html', form = form)

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        #Get form fields
        username = request.form['username']
        password_candidate = request.form['password']

        cur = mysql.connection.cursor()

        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            #Get the stored hash
            data = cur.fetchone()
            password = data['password']

            #compare passwords
            if sha256_crypt.verify(password_candidate, password):
                #Passed
                session['logged_in'] = True
                session['username'] = username

                flash("Inicio de sesión exitoso","Correcto")
                return redirect(url_for('dashboard'))
            else:
                error = 'Contraseña y/o Usuario invalido'
                return render_template('login.html', error=error)
            #Close connection
            cur.close()
        else:
            error = 'Usuario no encontrado'
            return render_template('login.html', error=error)
    return render_template('login.html')

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Por favor iniciar sesión','Peligro')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash("Se ha deslogeado", "Adios")
    return redirect(url_for('login'))

#Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    #create cursor
    cur=mysql.connection.cursor()
    cur=mysql.connection.cursor()

    result = cur.execute("SELECT product_id, location_id, qty FROM product_balance")

    products = cur.fetchall()
    cur.execute("SELECT location_id FROM locations")
    locations = cur.fetchall()
    locs = []
    for i in locations:
        locs.append(list(i.values())[0])

    if result>0:
        return render_template('dashboard.html', products = products, locations = locs)
    else:
        msg='Productos no encontrados'
        return render_template('dashboard.html', msg=msg)
    cur.close()


class ProductForm(Form):
    product_id = StringField('Product ID', [validators.Length(min=1, max=200)])

#Add Product
@app.route('/add_product', methods=['GET', 'POST'])
@is_logged_in
def add_product():
    form = ProductForm(request.form)
    if request.method == 'POST' and form.validate():
        product_id = form.product_id.data

        cur = mysql.connection.cursor()

        cur.execute("INSERT into products VALUES(%s)",(product_id,))

        mysql.connection.commit()

        cur.close()

        flash("Producto añadido con exito", "Genial")

        return redirect(url_for('products'))

    return render_template('add_product.html', form=form)

#Edit Product
@app.route('/edit_product/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_product(id):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM products where product_id = %s", [id])

    product = cur.fetchone()

    form = ProductForm(request.form)

    form.product_id.data = product['product_id']

    if request.method == 'POST' and form.validate():
        product_id = request.form['product_id']
        cur = mysql.connection.cursor()

        cur.execute("UPDATE products SET product_id=%s WHERE product_id=%s",(product_id, id))

        mysql.connection.commit()

        cur.close()

        flash("Producto actualizado", "Exito")

        return redirect(url_for('products'))

    return render_template('edit_product.html', form=form)

#Delete Product
@app.route('/delete_product/<string:id>', methods=['POST'])
@is_logged_in
def delete_product(id):
    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM products WHERE product_id=%s", [id])

    mysql.connection.commit()

    cur.close()

    flash("Producto eliminado", "Exito")

    return redirect(url_for('products'))

class LocationForm(Form):
    location_id = StringField('Location ID', [validators.Length(min=1, max=200)])

@app.route('/add_location', methods=['GET', 'POST'])
@is_logged_in
def add_location():
    form = LocationForm(request.form)
    if request.method == 'POST' and form.validate():
        location_id = form.location_id.data

        cur = mysql.connection.cursor()

        cur.execute("INSERT into locations VALUES(%s)",(location_id,))

        mysql.connection.commit()

        cur.close()

        flash("Ubicación añadida", "Exito")

        return redirect(url_for('locations'))

    return render_template('add_location.html', form=form)

#Edit Location
@app.route('/edit_location/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_location(id):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM locations where location_id = %s", [id])

    location = cur.fetchone()

    form = LocationForm(request.form)

    form.location_id.data = location['location_id']

    if request.method == 'POST' and form.validate():
        location_id = request.form['location_id']
        cur = mysql.connection.cursor()

        cur.execute("UPDATE locations SET location_id=%s WHERE location_id=%s",(location_id, id))

        mysql.connection.commit()

        cur.close()

        flash("Ubicación actualizada", "Exito")

        return redirect(url_for('locations'))

    return render_template('edit_location.html', form=form)

@app.route('/delete_location/<string:id>', methods=['POST'])
@is_logged_in
def delete_location(id):
    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM locations WHERE location_id=%s", [id])

    mysql.connection.commit()

    cur.close()

    flash("Ubicación borrada", "Exito")

    return redirect(url_for('locations'))


class ProductMovementForm(Form):
    from_location = SelectField('De', choices=[])
    to_location = SelectField('Hacia', choices=[])
    product_id = SelectField('Nombre de producto', choices=[])
    qty = IntegerField('Cantidad')

@app.route('/add_product_movements', methods=['GET', 'POST'])
@is_logged_in
def add_product_movements():
    form = ProductMovementForm(request.form) 
    cur = mysql.connection.cursor()
    cur.execute("SELECT product_id FROM products")
    products = cur.fetchall()
    prods = []
    for p in products:
        prods.append(list(p.values())[0])
    cur.execute("SELECT location_id FROM locations")
    locations = cur.fetchall()
    locs = []
    for i in locations:
        locs.append(list(i.values())[0])
    #app.logger.info(type(locations[0]))
    form.from_location.choices = [(l,l) for l in locs]
    form.from_location.choices.append(("--","--"))
    form.to_location.choices = [(l,l) for l in locs]
    form.to_location.choices.append(("--","--"))
    form.product_id.choices = [(p,p) for p in prods]
    if request.method == 'POST' and form.validate():
        from_location = form.from_location.data
        to_location = form.to_location.data
        product_id = form.product_id.data
        qty = form.qty.data
        #Create cursor
        cur = mysql.connection.cursor() 
        #execute
        cur.execute("INSERT into productmovements(from_location, to_location, product_id, qty) VALUES(%s, %s, %s, %s)",(from_location, to_location, product_id, qty))

        mysql.connection.commit()

        if from_location == "--":
            result = cur.execute("SELECT * from product_balance where location_id=%s and product_id=%s",(to_location, product_id))
            result = cur.fetchone()
            app.logger.info(result)
            if result!=None:
                if(len(result))>0:
                    Quantity = result["qty"]
                    q = Quantity + qty 
                    cur.execute("UPDATE product_balance set qty=%s where location_id=%s and product_id=%s",(q, to_location, product_id))
            else:
                cur.execute("INSERT into product_balance(product_id, location_id, qty) values(%s, %s, %s)",(product_id, to_location, qty))
        elif to_location == "--":
            result = cur.execute("SELECT * from product_balance where location_id=%s and product_id=%s",(from_location, product_id))
            result = cur.fetchone()
            app.logger.info(result)
            if result!=None:
                if(len(result))>0:
                    Quantity = result["qty"]
                    q = Quantity - qty 
                    cur.execute("UPDATE product_balance set qty=%s where location_id=%s and product_id=%s",(q, from_location, product_id))
            else:
                cur.execute("INSERT into product_balance(product_id, location_id, qty) values(%s, %s, %s)",(product_id, from_location, qty))
        else: 
            result = cur.execute("SELECT * from product_balance where location_id=%s and product_id=%s",(to_location, product_id))
            result = cur.fetchone()
            if result!=None:
                if(len(result))>0:
                    Quantity = result["qty"]
                    q = Quantity + qty 
                    cur.execute("UPDATE product_balance set qty=%s where location_id=%s and product_id=%s",(q, to_location, product_id))
            else:
                cur.execute("INSERT into product_balance(product_id, location_id, qty) values(%s, %s, %s)",(product_id, to_location, qty))
            
            result = cur.execute("SELECT * from product_balance where location_id=%s and product_id=%s",(from_location, product_id))
            result = cur.fetchone()
            if result!=None:
                if(len(result))>0:
                    Quantity = result["qty"]
                    q = Quantity - qty 
                    cur.execute("UPDATE product_balance set qty=%s where location_id=%s and product_id=%s",(q, from_location, product_id))
            else:
                cur.execute("INSERT into product_balance(product_id, location_id, qty) values(%s, %s, %s)",(product_id, from_location, qty))
        mysql.connection.commit()   

        cur.close()

        flash("Producto movido con exito", "Exito")

        return redirect(url_for('product_movements'))

    return render_template('add_product_movements.html', form=form)

@app.route('/edit_product_movement/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_product_movements(id):
    form = ProductMovementForm(request.form) 
    #Create cursor
    cur = mysql.connection.cursor()
    cur.execute("SELECT product_id FROM products")
    products = cur.fetchall()
    prods = []
    for p in products:
        prods.append(list(p.values())[0])
    cur.execute("SELECT location_id FROM locations")
    locations = cur.fetchall()
    locs = []
    for i in locations:
        locs.append(list(i.values())[0])
    #app.logger.info(type(locations[0]))
    form.from_location.choices = [(l,l) for l in locs]
    form.from_location.choices.append(("--","--"))
    form.to_location.choices = [(l,l) for l in locs]
    form.to_location.choices.append(("--","--"))
    form.product_id.choices = [(p,p) for p in prods]

    result = cur.execute("SELECT * FROM productmovements where movement_id = %s", [id])

    movement = cur.fetchone()

    form.from_location.data = movement['from_location']
    form.to_location.data = movement['to_location']
    form.product_id.data = movement['product_id']
    form.qty.data = movement['qty']

    if request.method == 'POST' and form.validate():
        from_location = request.form['from_location']
        to_location = request.form['to_location']
        product_id = request.form['product_id']
        qty = int(request.form['qty'])
        #create cursor
        cur = mysql.connection.cursor()

        cur.execute("UPDATE productmovements SET from_location=%s, to_location=%s, product_id=%s, qty=%s WHERE movement_id=%s",(from_location, to_location, product_id, qty, id))

        #commit to DB
        mysql.connection.commit()

        if from_location == "--":
            result = cur.execute("SELECT * from product_balance where location_id=%s and product_id=%s",(to_location, product_id))
            result = cur.fetchone()
            app.logger.info(result)
            if result!=None:
                if(len(result))>0:
                    Quantity = result["qty"]
                    q = Quantity + qty 
                    cur.execute("UPDATE product_balance set qty=%s where location_id=%s and product_id=%s",(q, to_location, product_id))
            else:
                cur.execute("INSERT into product_balance(product_id, location_id, qty) values(%s, %s, %s)",(product_id, to_location, qty))
        elif to_location == "--":
            result = cur.execute("SELECT * from product_balance where location_id=%s and product_id=%s",(from_location, product_id))
            result = cur.fetchone()
            app.logger.info(result)
            if result!=None:
                if(len(result))>0:
                    Quantity = result["qty"]
                    q = Quantity - qty 
                    cur.execute("UPDATE product_balance set qty=%s where location_id=%s and product_id=%s",(q, from_location, product_id))
            else:
                cur.execute("INSERT into product_balance(product_id, location_id, qty) values(%s, %s, %s)",(product_id, from_location, qty))
        else: 
            result = cur.execute("SELECT * from product_balance where location_id=%s and product_id=%s",(to_location, product_id))
            result = cur.fetchone()
            if result!=None:
                if(len(result))>0:
                    Quantity = result["qty"]
                    q = Quantity + qty 
                    cur.execute("UPDATE product_balance set qty=%s where location_id=%s and product_id=%s",(q, to_location, product_id))
            else:
                cur.execute("INSERT into product_balance(product_id, location_id, qty) values(%s, %s, %s)",(product_id, to_location, qty))
            
            result = cur.execute("SELECT * from product_balance where location_id=%s and product_id=%s",(from_location, product_id))
            result = cur.fetchone()
            if result!=None:
                if(len(result))>0:
                    Quantity = result["qty"]
                    q = Quantity - qty 
                    cur.execute("UPDATE product_balance set qty=%s where location_id=%s and product_id=%s",(q, from_location, product_id))
            else:
                cur.execute("INSERT into product_balance(product_id, location_id, qty) values(%s, %s, %s)",(product_id, from_location, qty))
        mysql.connection.commit()   

        flash("Movimiento de producto actualizado con exito", "Exito")

        return redirect(url_for('product_movements'))

    return render_template('edit_product_movements.html', form=form)

@app.route('/delete_product_movements/<string:id>', methods=['POST'])
@is_logged_in
def delete_product_movements(id):
    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM productmovements WHERE movement_id=%s", [id])

    mysql.connection.commit()

    cur.close()

    flash("Movimiento de producto eliminado", "Exito")

    return redirect(url_for('product_movements'))

if __name__ == '__main__':
    app.secret_key = "secret123"
    app.run(debug=True)
