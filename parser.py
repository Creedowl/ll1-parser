from collections import defaultdict
from typing import Dict, List, Union

from rich.console import Console
from rich.table import Table


class Parser:
    def __init__(self, begin: str, grammar: Dict[str, List[List[str]]]):
        self._begin = begin
        self._grammar = grammar
        self.left_recursion()
        self._terminals = set()
        self._nonTerminals = set()
        self._terminals.add("#")

        # get terminals and non-terminals, better to do this outside Parser
        for nonTerminal in grammar:
            self._nonTerminals.add(nonTerminal)
            for production in grammar[nonTerminal]:
                for i in production:
                    if not i.isupper():
                        self._terminals.add(i)

        self._first = self.get_first_set()
        self._follow = self.get_follow_set()
        self._table = self.create_analysis_table()

    def left_recursion(self):
        nonTerminals = [x for x in self._grammar]
        new = {}
        for i in range(len(nonTerminals)):
            pi = self._grammar[nonTerminals[i]]
            for j in range(i):
                pj = self._grammar[nonTerminals[j]]
                for k in range(len(pi)):
                    if pi[k][0] == nonTerminals[j]:
                        old = pi[k]
                        del pi[k]
                        for t in pj:
                            pi.append([*t, *old[1:]])
            l1: List[List[str]] = []
            l2: List[List[str]] = []
            for x in pi:
                if x[0] == nonTerminals[i]:
                    l1.append(x)
                else:
                    l2.append(x)
            if len(l1) == 0:
                continue
            newSymbol = nonTerminals[i] + "'"
            self._grammar[nonTerminals[i]] = [[*x, newSymbol] for x in l2]
            new[newSymbol] = [[*x[1:], newSymbol] for x in l1]
            new[newSymbol].append(["𝜺"])
        self._grammar.update(new)

    def get_first_set(self) -> Dict[Union[str, tuple], set]:
        first = defaultdict(set)
        while True:
            flag = True
            for nonTerminal in self._grammar:
                for production in self._grammar[nonTerminal]:
                    # X -> x... or X -> 𝜺
                    if (production[0] in self._terminals or production[0] == "𝜺") and \
                            production[0] not in first[nonTerminal]:
                        flag = False
                        first[nonTerminal].add(production[0])
                    elif production[0] in self._nonTerminals:  # X -> Y...
                        new = first[production[0]] - {"𝜺"} - first[nonTerminal]
                        # add first(Y)
                        if new:
                            flag = False
                            first[nonTerminal].update(new)
                        for i in range(len(production)):
                            # 𝜺 not in first(Y)
                            if "𝜺" not in first[production[i]]:
                                break
                            # 𝜺 in first(Y...)
                            elif i + 1 == len(production):
                                flag = False
                                first[nonTerminal].add("𝜺")
                            # Yi
                            elif production[i + 1] in self._nonTerminals:
                                new = first[production[i + 1]] - {"𝜺"} - first[nonTerminal]
                                if new:
                                    flag = False
                                    first[nonTerminal].update(new)
                            elif production[i + 1] in self._terminals and production[i + 1] not in first[nonTerminal]:
                                flag = False
                                first[nonTerminal].add(production[i + 1])
            if flag:
                break

        # sequence
        for nonTerminal in self._grammar:
            for production in self._grammar[nonTerminal]:
                for i in range(len(production)):
                    sequence = tuple(production[i:])
                    if sequence[0] in self._terminals or sequence[0] == "𝜺":
                        first[sequence] = {sequence[0]}
                    else:
                        first[sequence] = first[sequence[0]] - {"𝜺"}
                        for j in range(len(sequence)):
                            if "𝜺" not in first[sequence[j]]:
                                break
                            elif j + 1 == len(sequence):
                                first[sequence].add("𝜺")
                            else:
                                first[sequence].update(first[sequence[j + 1]] - {"𝜺"})
        # print(first)
        return first

    def get_follow_set(self) -> Dict[Union[str, tuple], set]:
        follow = defaultdict(set)
        follow[self._begin].add("#")
        while True:
            flag = True
            for nonTerminal in self._grammar:
                for production in self._grammar[nonTerminal]:
                    for i in range(len(production)):
                        if production[i] in self._terminals:
                            continue
                        # A -> 𝛼Y or A -> 𝛼Y𝛽, 𝜺 in 𝛽
                        if i + 1 == len(production) or "𝜺" in self._first[tuple(production[i + 1:])]:
                            new = follow[nonTerminal] - follow[production[i]]
                            if new:
                                flag = False
                                follow[production[i]].update(new)
                        # A -> 𝛼B𝛽
                        new = self._first[tuple(production[i + 1:])] - {"𝜺"} - follow[production[i]]
                        if new:
                            flag = False
                            follow[production[i]].update(new)
            if flag:
                break
        # print(follow)
        return follow

    def create_analysis_table(self) -> Dict[str, Dict[str, List]]:
        table = defaultdict(lambda: defaultdict(list))
        for nonTerminal in self._nonTerminals:
            for production in self._grammar[nonTerminal]:
                for terminal in self._first[tuple(production)]:
                    if terminal not in self._first[tuple(production)]:
                        continue
                    if terminal == "𝜺":
                        for i in self._follow[nonTerminal]:
                            table[nonTerminal][i] = production
                    else:
                        table[nonTerminal][terminal] = production
        # print(table)
        return table

    def analysis(self, inp: str):
        print("\n")
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("step")
        table.add_column("symbols")
        table.add_column("inputs")
        table.add_column("production")
        symbols = ["#", self._begin]
        inputS = [*(inp + "#")]
        inputS.reverse()
        count = 0
        production = ""
        while True:
            table.add_row(str(count), "".join(symbols), "".join(inputS), production)
            production = ""
            count += 1
            # X = a = #, success
            if symbols[-1] == inputS[-1] and symbols[-1] == "#":
                break
            # X = a != #, next input
            elif symbols[-1] == inputS[-1]:
                symbols.pop()
                inputS.pop()
            # use production
            elif symbols[-1] in self._nonTerminals:
                pro = self._table[symbols[-1]][inputS[-1]]
                if pro:
                    production = f"{symbols[-1]} -> {''.join(pro)}"
                    symbols.pop()
                    for i in reversed(pro):
                        if i == "𝜺":
                            continue
                        symbols.append(i)
                else:
                    console.print(f"No productions for {symbols[-1]} and {inputS[-1]}", style="bold red")
                    break
            else:
                console.print("Bad behavior here", style="bold red")
                break

        print("analysis progress")
        console.print(table)

    def show(self):
        print("grammar: ")
        for nonTerminal in self._grammar:
            s = ""
            for production in self._grammar[nonTerminal]:
                s += "".join(production) + " | "
            s = s.strip().rstrip("|")
            print(f"{nonTerminal} -> {s}")
        print("\nfirst set: ")
        for nonTerminal in self._first:
            if not type(nonTerminal) == str:
                continue
            print(f"{nonTerminal}: {self._first[nonTerminal]}")
        print("\nfollow set: ")
        for nonTerminal in self._follow:
            print(f"{nonTerminal}: {self._follow[nonTerminal]}")

        print("\nanalysis table: ")
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("")
        for terminal in self._terminals:
            if terminal != "𝜺":
                table.add_column(terminal)
        for nonTerminal in self._nonTerminals:
            res = [nonTerminal]
            for terminal in self._terminals:
                if terminal == "𝜺":
                    continue
                res.append("".join(self._table[nonTerminal][terminal]))
            table.add_row(*res)
        console.print(table)


if __name__ == '__main__':
    with open("in.txt", "r") as f:
        inputs = {}
        start = ""
        for line in f:
            line = line.lstrip().rstrip().replace(" ", "")
            temp = line.split("->")
            if start == "":
                start = temp[0]
            inputs[temp[0]] = [[*x] for x in temp[1].split("|")]
        parser = Parser(start, inputs)
        parser.show()
        parser.analysis("i*i+i")
