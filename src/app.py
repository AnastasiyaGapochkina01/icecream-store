from flask import Flask, request, jsonify
from .database import SessionLocal, engine, Base
from .models import IceCream
from prometheus_client import make_wsgi_app, Counter, Histogram, Gauge, generate_latest
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import time
app = Flask(__name__)

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)


# Создаем метрики Prometheus
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'Duration of HTTP requests in seconds',
    ['method', 'endpoint', 'status']
)

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

DB_SESSION_GAUGE = Gauge(
    'db_sessions_active',
    'Number of active database sessions'
)

ICE_CREAM_COUNT = Gauge(
    'ice_cream_total_count',
    'Total number of ice creams in database'
)

ERROR_COUNT = Counter(
    'app_errors_total',
    'Total number of application errors',
    ['type']
)

# Middleware для сбора метрик
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    # Пропускаем метрики, чтобы не учитывать их в статистике
    if request.path == '/metrics':
        return response
        
    duration = time.time() - request.start_time
    REQUEST_DURATION.labels(
        request.method, 
        request.path, 
        response.status_code
    ).observe(duration)
    
    REQUEST_COUNT.labels(
        request.method, 
        request.path, 
        response.status_code
    ).inc()
    
    return response

# Функция для обновления метрик
def update_metrics():
    session = SessionLocal()
    try:
        # Обновляем количество мороженого
        count = session.query(IceCream).count()
        ICE_CREAM_COUNT.set(count)
        
        # Обновляем количество активных сессий (примерное)
        DB_SESSION_GAUGE.set(len(session.registry()))
    except Exception as e:
        ERROR_COUNT.labels(type='metrics_update').inc()
        print(f"Metrics update error: {e}")
    finally:
        session.close()

# Эндпоинт для метрик
@app.route('/metrics')
def metrics():
    update_metrics()
    return generate_latest(), 200, {'Content-Type': 'text/plain'}

# Добавляем middleware для обработки ошибок
@app.errorhandler(Exception)
def handle_exception(e):
    ERROR_COUNT.labels(type='http_exception').inc()
    return jsonify({"error": "Internal server error"}), 500

@app.route("/ice_creams", methods=["POST"])
def create_ice_cream():
    data = request.json
    session = SessionLocal()
    try:
        ice_cream = IceCream(
            name=data['name'],
            description=data.get('description', ''),
            price=data['price'],
            quantity=data.get('quantity', 0)
        )
        session.add(ice_cream)
        session.commit()
        return jsonify({"id": ice_cream.id}), 201
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        session.close()

@app.route("/ice_creams", methods=["GET"])
def read_ice_creams():
    session = SessionLocal()
    ice_creams = session.query(IceCream).all()
    result = [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "price": item.price,
            "quantity": item.quantity
        } for item in ice_creams
    ]
    session.close()
    return jsonify(result)

@app.route("/ice_creams/<int:id>", methods=["PUT"])
def update_ice_cream(id):
    data = request.json
    session = SessionLocal()
    try:
        ice_cream = session.query(IceCream).filter(IceCream.id == id).first()
        if not ice_cream:
            return jsonify({"error": "Ice cream not found"}), 404
        
        if 'name' in data: ice_cream.name = data['name']
        if 'description' in data: ice_cream.description = data['description']
        if 'price' in data: ice_cream.price = data['price']
        if 'quantity' in data: ice_cream.quantity = data['quantity']
        
        session.commit()
        return jsonify({"message": "Updated successfully"})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        session.close()

@app.route("/ice_creams/<int:id>", methods=["DELETE"])
def delete_ice_cream(id):
    session = SessionLocal()
    try:
        ice_cream = session.query(IceCream).filter(IceCream.id == id).first()
        if not ice_cream:
            return jsonify({"error": "Ice cream not found"}), 404
        
        session.delete(ice_cream)
        session.commit()
        return jsonify({"message": "Deleted successfully"})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        session.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
