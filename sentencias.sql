CREATE TABLE IF NOT EXISTS programas (
    codcarrera INTEGER PRIMARY KEY AUTOINCREMENT,
    descarrera TEXT NOT NULL UNIQUE
);

INSERT INTO programas (descarrera) VALUES
('Ingeniería en Sistemas de Información'),
('Licenciatura en Sistemas de Información'),
('Tecnicatura en Programación'),
('Tecnicatura en Análisis de Sistemas'),
('Tecnicatura en Redes y Telecomunicaciones');
