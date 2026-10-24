-- 001_schema.sql
-- Schema für Student / Module / Grade mit ein paar Seeddaten

create table if not exists student (
  student_id   serial primary key,
  matrikel     text not null unique,
  vorname      text not null,
  nachname     text not null,
  programme    text not null,
  semester     int  not null check (semester between 1 and 12)
);

create table if not exists module (
  module_id    serial primary key,
  name         text not null unique
);

create table if not exists grade (
  grade_id     serial primary key,
  student_id   int not null references student(student_id) on delete cascade,
  module_id    int not null references module(module_id) on delete cascade,
  grade_value  text not null,
  graded_at    timestamp not null default now()
);

insert into student (matrikel, vorname, nachname, programme, semester) values
  ('12345', 'Anna', 'Koch', 'Informatik', 3),
  ('23456', 'Ben', 'König', 'Wirtschaftsinformatik', 2),
  ('34567', 'Clara', 'Meier', 'Data Science', 4)
on conflict (matrikel) do nothing;

insert into module (name) values
  ('Datenbanken'),
  ('Programmierung 1'),
  ('Software Engineering'),
  ('Mathematik 1')
on conflict (name) do nothing;

insert into grade (student_id, module_id, grade_value)
select s.student_id, m.module_id, g.grade_value
from (values
  ('12345', 'Datenbanken',       '1,7'),
  ('12345', 'Programmierung 1',  '2,0'),
  ('23456', 'Datenbanken',       '2,3'),
  ('23456', 'Mathematik 1',      '1,3'),
  ('34567', 'Software Engineering', '1,0')
) as g(matrikel, modulname, grade_value)
join student s on s.matrikel = g.matrikel
join module m on m.name = g.modulname
on conflict do nothing;
