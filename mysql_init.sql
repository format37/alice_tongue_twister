create database fastwords;
use fastwords;

create table users(id int not null auto_increment,user varchar(128) not null,name varchar(36) not null, menu_id int, primary key(id));
alter table users convert to character set utf8mb4 collate utf8mb4_unicode_ci;

create table words(id int not null auto_increment,word varchar(1024) not null,primary key(id));
alter table words convert to character set utf8mb4 collate utf8mb4_unicode_ci;

create table scores(id int not null auto_increment,user varchar(128) not null, word_id int, score int, event_date DATETIME, primary key(id));

create table log(id int not null auto_increment,user varchar(128), menu int, text_in varchar(1024), text_out varchar(1024), event_date DATETIME, primary key(id));
alter table log convert to character set utf8mb4 collate utf8mb4_unicode_ci;

exit;
