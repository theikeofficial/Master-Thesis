# Master Thesis

> **Primena grafovskih neuronskih mreža na predviđanje vremena izvršavanja SAT rešavača**

Kratak opis rada: Cilj ovog rada je predviđanje vremena izvršavanja SAT rešavača korišćenjem grafovskih neuronskih mreža i evaluacija pogodnosti tog pristupa za konstrukciju portfolija SAT rešavača. Grafovske neuronske mreže rade direktno nad grafovskim reprezentacijama formula iskazne logike, umesto nad specifično definisanim skalarnim atributima. Kako je već poznato da neuronske mreže koje rade nad izvornim reprezentacijama podataka (što za iskazne formule mogu biti grafovi) često po performansama prestižu sisteme zasnovane na atributima koje su definisali ljudi, postoji osnov da se očekuju bolji rezultati od do sada postignutih. S druge strane, ova vrsta neuronskih mreža može biti računski zahtevnija za primenu. Otud je potrebno evaluirati njihov potencijal za realnu primenu. Uspeh odabranih metoda biće upoređenjen sa klasifikatorima koji su do sada demonstrirali veliki uspeh: _k-najbližih suseda_ i _šume nasumičnih stabala_. Eksperimenti će biti izvršeni korišćenjem programskih jezika Python i C++. Podaci će biti odabrani iz korpusa sa takmičenja SAT Competition.

Rad: [ovde](http://poincare.matf.bg.ac.rs/~nikolic//NikolaAjzenhamerMaster.pdf)

---

> **Using graph neural networks for predicting the running time of SAT solvers**

Abstract: The idea behind this thesis is to predict the running time of SAT solvers using graph neural networks and test such approach in constructing SAT portfolio. Graph neural network operate over graph representation of propositional calculus formulae instead of specifically crafted scalar data. As it is familiar, neural networks operate over raw data representations (which can be graphs for propositional calculus formulae) and provide better performance over systems that are applied on attributes crafted by humans. Thus, it is plausible to believe that this approach would lead to better results than what had been achieved so far. On the other hand, this neural network type can be difficult to use in practical cases, due to its expensive computational complexity. Because of this, it is important to evaluate the practicality of such a system. The success of chosen methods will be compared to classifiers which had proven their success in the past: _k-nearest neighbours_ and _random forests_. The experiments will be achieved using programming languages Python and C++. The data will be selected from the corpus of SAT competition.

Thesis (in Serbian): [here](http://poincare.matf.bg.ac.rs/~nikolic//NikolaAjzenhamerMaster.pdf)
