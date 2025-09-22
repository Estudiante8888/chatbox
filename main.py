from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/base")
def base():
    return render_template('base.html')

@app.route("/mision")
def mision():
    return render_template('mision.html')

@app.route("/vision", methods=['GET', 'POST'])
def vision():
    if request.method == 'POST':
        print(request.form)
    return render_template('vision.html')

@app.route("/programas")
def programas():
    return render_template('programas.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)