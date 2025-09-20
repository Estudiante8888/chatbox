CREATE TABLE IF NOT EXISTS carrera (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descripcion TEXT NOT NULL UNIQUE
);

INSERT INTO carrera (descripcion) VALUES
('Ingeniería en Sistemas de Información'),
('Licenciatura en Sistemas de Información'),
('Tecnicatura en Programación'),
('Tecnicatura en Análisis de Sistemas'),
('Tecnicatura en Redes y Telecomunicaciones');
