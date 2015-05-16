from lma import app

if __name__ == '__main__':
    app.config['DEBUG'] = True
    app.run(host='127.0.0.1', port=8000)
