# Single-Column Notation — Examples

A collection of examples showing how common structured data patterns look in SCN. All values are returned as strings by the parser.

---

## 1. Simple Key-Value Config

A flat configuration with scalar values.

**SCN:**
~~~
[settings]
app_name:
TaskTracker
version:
1.4
debug:
false
max_retries:
3
api_key:
sk-abc123xyz
~~~

**Resulting dict:**
~~~json
{
  "settings": {
    "app_name": "TaskTracker",
    "version": "1.4",
    "debug": "false",
    "max_retries": "3",
    "api_key": "sk-abc123xyz"
  }
}
~~~

---

## 2. Nested Keys with Dot Notation

Group related settings without extra sections.

**SCN:**
~~~
[email]
smtp.host:
mail.example.com
smtp.port:
587
smtp.tls:
true
sender.name:
No Reply
sender.address:
noreply@example.com
~~~

**Resulting dict:**
~~~json
{
  "email": {
    "smtp": {
      "host": "mail.example.com",
      "port": "587",
      "tls": "true"
    },
    "sender": {
      "name": "No Reply",
      "address": "noreply@example.com"
    }
  }
}
~~~

---

## 3. Simple Lists

A key followed by dash items.

**SCN:**
~~~
[project]
name:
website-redesign

languages:
- python
- javascript
- sql

ignored_dirs:
- node_modules
- .git
- __pycache__
- dist
~~~

**Resulting dict:**
~~~json
{
  "project": {
    "name": "website-redesign",
    "languages": ["python", "javascript", "sql"],
    "ignored_dirs": ["node_modules", ".git", "__pycache__", "dist"]
  }
}
~~~

---

## 4. Comments

Comments are lines starting with `;;`. They are ignored everywhere.

**SCN:**
~~~
[server]
;; primary database host
host:
db.example.com

;; default postgres port
port:
5432

backups:
;; daily snapshots
- daily-01
- daily-02
;; weekly snapshots
- weekly-01
~~~

**Resulting dict:**
~~~json
{
  "server": {
    "host": "db.example.com",
    "port": "5432",
    "backups": ["daily-01", "daily-02", "weekly-01"]
  }
}
~~~



---

## 5. List of Dicts — Basic

A simple table-like structure using +name.

**SCN:**
~~~
[contacts]
+people
name:
Alice Johnson
email:
alice@example.com
phone:
555-0101
+people
name:
Bob Smith
email:
bob@example.com
phone:
555-0102
+people
name:
Carol Davis
email:
carol@example.com
phone:
555-0103
~~~

**Resulting dict:**
~~~json
{
  "contacts": {
    "people": [
      {"name": "Alice Johnson", "email": "alice@example.com", "phone": "555-0101"},
      {"name": "Bob Smith", "email": "bob@example.com", "phone": "555-0102"},
      {"name": "Carol Davis", "email": "carol@example.com", "phone": "555-0103"}
    ]
  }
}
~~~

---

## 6. Dict List with Nested Dot Keys

Dot notation works inside +name blocks.

**SCN:**
~~~
[apis]
+endpoints
path:
/users
method:
GET
rate_limit.requests:
100
rate_limit.window_seconds:
60
+endpoints
path:
/users
method:
POST
rate_limit.requests:
20
rate_limit.window_seconds:
60
auth.required:
true
auth.scheme:
bearer
~~~

**Resulting dict:**
~~~json
{
  "apis": {
    "endpoints": [
      {
        "path": "/users",
        "method": "GET",
        "rate_limit": {"requests": "100", "window_seconds": "60"}
      },
      {
        "path": "/users",
        "method": "POST",
        "rate_limit": {"requests": "20", "window_seconds": "60"},
        "auth": {"required": "true", "scheme": "bearer"}
      }
    ]
  }
}
~~~

---

## 7. Lists Inside Dict List Entries

Each dict entry can have its own scalar lists.

**SCN:**
~~~
[recipes]
+items
name:
Pancakes
prep_minutes:
5
cook_minutes:
15
ingredients:
- flour
- eggs
- milk
- butter
- sugar
+items
name:
Salad
prep_minutes:
10
cook_minutes:
0
ingredients:
- lettuce
- tomato
- cucumber
- dressing
~~~

**Resulting dict:**
~~~json
{
  "recipes": {
    "items": [
      {
        "name": "Pancakes",
        "prep_minutes": "5",
        "cook_minutes": "15",
        "ingredients": ["flour", "eggs", "milk", "butter", "sugar"]
      },
      {
        "name": "Salad",
        "prep_minutes": "10",
        "cook_minutes": "0",
        "ingredients": ["lettuce", "tomato", "cucumber", "dressing"]
      }
    ]
  }
}
~~~

---

## 8. Nested Dict Lists (List of Dicts Inside List of Dicts)

The core nesting feature.

**SCN:**
~~~
[school]
+classes
name:
Biology 101
room:
SCI-201
+students
name:
Emma
grade:
A
+students
name:
James
grade:
B+
+classes
name:
History 201
room:
HUM-105
+students
name:
Olivia
grade:
A-
+students
name:
Liam
grade:
B
+students
name:
Sophia
grade:
A
~~~

**Resulting dict:**
~~~json
{
  "school": {
    "classes": [
      {
        "name": "Biology 101",
        "room": "SCI-201",
        "students": [
          {"name": "Emma", "grade": "A"},
          {"name": "James", "grade": "B+"}
        ]
      },
      {
        "name": "History 201",
        "room": "HUM-105",
        "students": [
          {"name": "Olivia", "grade": "A-"},
          {"name": "Liam", "grade": "B"},
          {"name": "Sophia", "grade": "A"}
        ]
      }
    ]
  }
}
~~~

---

## 9. Three Levels of Nesting

Dicts inside dicts inside dicts.

**SCN:**
~~~
[company]
+departments
name:
Engineering
+teams
name:
Backend
+members
name:
Alice
role:
senior
+members
name:
Bob
role:
mid
+teams
name:
Frontend
+members
name:
Carol
role:
lead
+departments
name:
Marketing
+teams
name:
Content
+members
name:
Dave
role:
writer
+members
name:
Eve
role:
editor
~~~

**Resulting dict:**
~~~json
{
  "company": {
    "departments": [
      {
        "name": "Engineering",
        "teams": [
          {
            "name": "Backend",
            "members": [
              {"name": "Alice", "role": "senior"},
              {"name": "Bob", "role": "mid"}
            ]
          },
          {
            "name": "Frontend",
            "members": [
              {"name": "Carol", "role": "lead"}
            ]
          }
        ]
      },
      {
        "name": "Marketing",
        "teams": [
          {
            "name": "Content",
            "members": [
              {"name": "Dave", "role": "writer"},
              {"name": "Eve", "role": "editor"}
            ]
          }
        ]
      }
    ]
  }
}
~~~

---

## 10. Multiple Sections Working Together

A full application config using several sections.

**SCN:**
~~~
[app]
name:
Acme Portal
version:
2.0
environment:
production

[database]
connection.host:
db.acme.com
connection.port:
5432
connection.name:
acme_prod
pool.min:
5
pool.max:
20

[cache]
enabled:
true
backend:
redis
ttl_seconds:
300
hosts:
- redis-1.acme.com
- redis-2.acme.com

[logging]
level:
info
format:
json
+outputs
type:
console
colorize:
true
+outputs
type:
file
path:
/var/log/acme/app.log
rotate.max_mb:
100
rotate.keep:
5
+outputs
type:
syslog
host:
logs.acme.com
port:
514

[feature_flags]
new_dashboard:
true
beta_search:
false
dark_mode:
true
~~~

**Resulting dict:**
~~~json
{
  "app": {
    "name": "Acme Portal",
    "version": "2.0",
    "environment": "production"
  },
  "database": {
    "connection": {"host": "db.acme.com", "port": "5432", "name": "acme_prod"},
    "pool": {"min": "5", "max": "20"}
  },
  "cache": {
    "enabled": "true",
    "backend": "redis",
    "ttl_seconds": "300",
    "hosts": ["redis-1.acme.com", "redis-2.acme.com"]
  },
  "logging": {
    "level": "info",
    "format": "json",
    "outputs": [
      {"type": "console", "colorize": "true"},
      {"type": "file", "path": "/var/log/acme/app.log", "rotate": {"max_mb": "100", "keep": "5"}},
      {"type": "syslog", "host": "logs.acme.com", "port": "514"}
    ]
  },
  "feature_flags": {
    "new_dashboard": "true",
    "beta_search": "false",
    "dark_mode": "true"
  }
}
~~~

---

## 11. No Sections (Root-Level Keys)

Sections are optional. Keys can live at the root.

**SCN:**
~~~
title:
My Document
author:
Jane Doe
created:
2025-01-15
tags:
- draft
- internal
- review
~~~

**Resulting dict:**
~~~json
{
  "title": "My Document",
  "author": "Jane Doe",
  "created": "2025-01-15",
  "tags": ["draft", "internal", "review"]
}
~~~

---

## 12. CI/CD Pipeline Definition

A practical devops example.

**SCN:**
~~~
[pipeline]
name:
deploy-api
trigger.branch:
main
trigger.on_merge:
true

;; unit tests and coverage
+stages
name:
test
image:
python:3.12
commands:
- pip install -r requirements.txt
- pytest --cov

;; build and push container
+stages
name:
build
image:
docker:latest
commands:
- docker build -t api:latest .
- docker push registry.io/api:latest
depends_on:
- test

;; roll out to cluster
+stages
name:
deploy
image:
kubectl:1.28
commands:
- kubectl apply -f k8s/
depends_on:
- build
+notifications
event:
failure
channel:
#alerts
+notifications
event:
success
channel:
#deployments
~~~

**Resulting dict:**
~~~json
{
  "pipeline": {
    "name": "deploy-api",
    "trigger": {"branch": "main", "on_merge": "true"},
    "stages": [
      {
        "name": "test",
        "image": "python:3.12",
        "commands": ["pip install -r requirements.txt", "pytest --cov"]
      },
      {
        "name": "build",
        "image": "docker:latest",
        "commands": ["docker build -t api:latest .", "docker push registry.io/api:latest"],
        "depends_on": ["test"]
      },
      {
        "name": "deploy",
        "image": "kubectl:1.28",
        "commands": ["kubectl apply -f k8s/"],
        "depends_on": ["build"],
        "notifications": [
          {"event": "failure", "channel": "#alerts"},
          {"event": "success", "channel": "#deployments"}
        ]
      }
    ]
  }
}
~~~



---

## 13. E-Commerce Product Catalog

Products with variants and tags.

**SCN:**
~~~
[catalog]
store:
Acme Goods
currency:
USD

+products
sku:
SHIRT-001
name:
Classic Tee
price:
29.99
tags:
- clothing
- cotton
- unisex
+variants
size:
S
stock:
45
+variants
size:
M
stock:
120
+variants
size:
L
stock:
88

+products
sku:
MUG-042
name:
Developer Mug
price:
14.99
tags:
- accessories
- kitchen
+variants
color:
black
stock:
200
+variants
color:
white
stock:
150
~~~

**Resulting dict:**
~~~json
{
  "catalog": {
    "store": "Acme Goods",
    "currency": "USD",
    "products": [
      {
        "sku": "SHIRT-001",
        "name": "Classic Tee",
        "price": "29.99",
        "tags": ["clothing", "cotton", "unisex"],
        "variants": [
          {"size": "S", "stock": "45"},
          {"size": "M", "stock": "120"},
          {"size": "L", "stock": "88"}
        ]
      },
      {
        "sku": "MUG-042",
        "name": "Developer Mug",
        "price": "14.99",
        "tags": ["accessories", "kitchen"],
        "variants": [
          {"color": "black", "stock": "200"},
          {"color": "white", "stock": "150"}
        ]
      }
    ]
  }
}
~~~

---

## 14. Empty Rows for Readability

Empty rows can be inserted anywhere without affecting the output. These two are equivalent:

**Compact:**
~~~
[db]
host:
localhost
port:
5432
+tables
name:
users
+tables
name:
orders
~~~

**Spaced out:**
~~~
[db]

host:
localhost

port:
5432

+tables
name:
users

+tables
name:
orders
~~~

Both produce the same dict.
