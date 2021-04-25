# ciffiro_search_engine

Проект представляет собой поисковый движок по части дампа Википедии. <br> 
Реализован следующий функционал:
* Булев поиск
* Цитатный поиск
* Нечеткий поиск
* Ранжирование результатов по TF-IDF
* Ускорение с помощью прыжков по индексу (Jump Tables)
* Сжатие с помощью Simple9
* Зонный поиск (заголовок статьи + ее содержание) 

Индекс имеет следующее бинарное представление:
![exampleImage1](https://i.ibb.co/2hHNr1M/5.png)

Синтаксис поисковых запросов:
* Если в запросе между терамами только пробелы, то используется нечеткий поиск
* Иначе используется булев поиск
* Пробел или два амперсанда, «&&», соответствуют логической операции «И»
* Две вертикальных «палочки», «||» –логическая операция «ИЛИ» 
* Восклицательный знак, «!» –логическая операция «НЕТ»
* Используются скобки трех видов (), [], {}
* "" кавычки, включают режим цитатного поиска для терминов внутрикавычек.
* "request" / n допускаются вкрапления других терминов так, чтобы расстояние от первого термина цитаты до последнего непревышало бы n 

Примеры поисковой выдачи:
![exampleImage2](https://i.ibb.co/60Hk4m2/1.png)
![exampleImage3](https://i.ibb.co/4Z98xXP/2.png)
![exampleImage4](https://i.ibb.co/W0k4NL6/3.png)
![exampleImage5](https://i.ibb.co/vHfrN45/4.png)
