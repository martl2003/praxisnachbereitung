create table if not exists student (
  id serial primary key,
  first_name text not null,
  surname text not null,
  matrikel text not null unique,
  semester integer not null
);

insert into student (matrikel, first_name, surname, semester) values
  ('2021001','John','Doe',3),
  ('2021002','Jane','Smith',4),
  ('2021003','Bob','Johnson',3),
  ('2021004','Alice','Williams',6),
  ('2021005','Charlie','Brown',3),
  ('2021006','David','Miller',8),
  ('2021007','Emily','Davis',9),
  ('2021008','Frank','Wilson',10),
  ('2021009','Grace','Moore',9),
  ('2021010','Henry','Taylor',6);

create or replace view v_student_status as
select semester, count(*) as cnt
from student
group by semester;
