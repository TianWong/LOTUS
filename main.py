import os
import sys
import re
from cmd import Cmd
import queue
from typing import Tuple
import yaml
import ipaddress
import itertools
import gc

class IP_address_generator:
  def __init__(self):
    self.index = 1 # To generate unique address

  def get_unique_address(self):
    address = "10." + str(self.index // 256) + "." + str(self.index % 256) + ".0/24"
    self.index += 1
    return address

class AS_class:
  def __init__(self, asn, address, country, rank):
    self.as_number = asn
    self.network_address = address
    self.country = country
    self.rank = rank
    self.policy = ["LocPrf", "PathLength"]
    self.routing_table = Routing_table(self.network_address, self.policy)

  def show_info(self, only_best=False, address=None):
    print("====================")
    print(f"AS NUMBER: {self.as_number}")
    print(f"network: {self.network_address}")
    print(f"policy: {self.policy}")

    table = self.routing_table.get_table()
    addr_list = []
    if address == None:
      for addr in table.keys():
        addr_list.append(ipaddress.ip_network(addr))
      addr_list.sort()
    else:
      addr_list.append(address)

    print("routing table: (best path: > )")
    for addr in addr_list:
      print(str(addr) + ":")
      try:
        for r in table[str(addr)]:
          path = r["path"]
          come_from = r["come_from"]
          LocPrf = r["LocPrf"]
          try:
            aspv = r["aspv"]
            if r["best_path"] == True:
              print(f"> path: {path}, LocPrf: {LocPrf}, come_from: {come_from}, aspv: {aspv}")
            elif only_best == True:
              continue
            else:
              print(f"  path: {path}, LocPrf: {LocPrf}, come_from: {come_from}, aspv: {aspv}")
          except KeyError:
            if r["best_path"] == True:
              print(f"> path: {path}, LocPrf: {LocPrf}, come_from: {come_from}")
            elif only_best == True:
              continue
            else:
              print(f"  path: {path}, LocPrf: {LocPrf}, come_from: {come_from}")
      except KeyError:
        print("No-Path")
    print("====================")

  def set_public_aspa(self, public_aspa_list):
    self.routing_table.set_public_aspa(public_aspa_list)

  def update(self, update_message):
    if self.as_number in update_message["path"].split("-"):
      return

    route_diff = self.routing_table.update(update_message)
    if route_diff == None:
      return
    else:
      prev_best, new_best = route_diff
      new_best["path"] = str(self.as_number) + "-" + new_best["path"]
      if prev_best:
        prev_best["path"] = str(self.as_number) + "-" + prev_best["path"]
      return prev_best, new_best

  def change_ASPV(self, message):
    if message["switch"] == "on":
      self.policy = ["LocPrf", "PathLength"]
      self.policy.insert(int(message["priority"]) - 1, "aspv")
    elif message["switch"] == "off":
      self.policy = ["LocPrf", "PathLength"]
    self.routing_table.change_policy(self.policy)
    if "aspv_local_prf" in message:
      self.routing_table.change_aspv_local_prf(message["aspv_local_prf"] == "True")

  def receive_init(self, init_message):
    best_path_list = self.routing_table.get_best_path_list()
    new_update_message_list = []
    update_src = self.as_number
    update_dst = init_message["src"]
    if init_message["come_from"] == "customer":
      for r in best_path_list:
        if r["path"] == "i": # the network is the AS itself
          new_update_message_list.append({"src": update_src, "dst": update_dst, "path": update_src, "network": r["network"]})
        else:
          new_update_message_list.append({"src": update_src, "dst": update_dst, "path": update_src + "-" + r["path"], "network": r["network"]})
    else:
      for r in best_path_list:
        if r["path"] == "i": # the network is the AS itself
            new_update_message_list.append({"src": update_src, "dst": update_dst, "path": update_src, "network": r["network"]})
        elif r["come_from"] == "customer":
            new_update_message_list.append({"src": update_src, "dst": update_dst, "path": update_src + "-" + r["path"], "network": r["network"]})
    return new_update_message_list

class AS_class_list:
  def __init__(self):
    self.class_list = {}
    self.ip_gen = IP_address_generator()

  def add_AS(self, as_number, country=None, rank=100):
    if not as_number in self.class_list.keys():
      self.class_list[as_number] = AS_class(as_number, self.ip_gen.get_unique_address(), country, rank)
    else:
      print("Error: AS " + str(as_number) + " is already registered.", file=sys.stderr)

  def show_AS_list(self, sort_flag, best_flag, address):

    keys = list(self.class_list.keys())
    if sort_flag == True:
      keys.sort()

    for k in keys:
      self.class_list[k].show_info(only_best=best_flag, address=address)

  def get_AS(self, as_number) -> AS_class:
    return self.class_list[as_number]

  def get_AS_list(self):
    return self.class_list

  def import_AS_list(self, import_list):

    self.class_list = {}
    for a in import_list:
      self.class_list[a["AS"]] = AS_class(a["AS"], a["network_address"])
      self.class_list[a["AS"]].policy = a["policy"]
      self.class_list[a["AS"]].routing_table.change_policy(a["policy"])
      self.class_list[a["AS"]].routing_table.table = a["routing_table"]


class Routing_table:
  def __init__(self, network, policy):
    self.table = {}
    self.table[network] = [{"path": "i", "come_from": "customer", "LocPrf": 1000, "best_path": True}]
    self.policy = policy
    self.aspa_list = {}
    self.aspv_local_prf = False
  
  def change_aspv_local_prf(self, prf):
    self.aspv_local_prf = prf

  def change_policy(self, policy):
    self.policy = policy

  def set_public_aspa(self, public_aspa_list):
    self.aspa_list = public_aspa_list

  def verify_pair(self, customer_as, provider_as):
    try:
      candidate_provider_list = self.aspa_list[customer_as]
    except KeyError:
      return "Unknown"

    if provider_as in candidate_provider_list:
      return "Valid"
    else:
      return "Invalid"

  def aspv(self, route, neighbor_as):

    ###
    ### Referencing Internet-Draft draft-ietf-sidrops-aspa-verification-08
    ### https://www.ietf.org/archive/id/draft-ietf-sidrops-aspa-verification-08.txt
    ###

    p = route["path"]
    path_list = p.split("-")

    if re.fullmatch("customer|peer", route["come_from"]):

      if path_list[0] != neighbor_as:
        return "Invalid"

      try:
        index = -1
        semi_state = "Valid"
        while True:
          pair_check = self.verify_pair(path_list[index], path_list[index - 1])
          if pair_check == "Invalid":
            return "Invalid"
          elif pair_check == "Unknown":
            semi_state = "Unknown"
          index -= 1
      except IndexError:  # the end of checking
        pass

      return semi_state

    elif route["come_from"] == "provider":

      if path_list[0] != neighbor_as:
        return "Invalid"
      
      # trivially valid case
      if len(path_list) >= 1 and len(path_list) <= 2:
        return "Valid"
      
      path_list.reverse()

      umin = len(path_list) + 1
      vmax = 0
      K = 1
      L = len(path_list)
      chain_flag = True

      for i in range(len(path_list)):
        pair_check = self.verify_pair(path_list[i], path_list[i+1])
        if pair_check != "Valid" and chain_flag:
          chain_flag = False
          K = i
        elif pair_check == "Invalid":
          umin = i + 1
          break

      chain_flag = True
      for i in range(len(path_list), 0, -1):
        pair_check = self.verify_pair(path_list[i], path_list[i-1])
        if pair_check != "Valid" and chain_flag:
          chain_flag = False
          L = i
        elif pair_check == "Invalid":
          vmax = i + 1
          break

        if umin <= vmax:
          return "Invalid"
        elif L - K <= 1:
          return "Valid"
        return "Unknown"

  def update(self, update_message) -> None | Tuple[None | dict, dict]:
    """
    attempts an update to the routing table
    returns a (prev_best_route, new_best_route) tuple on best route change, or None
    prev_best_route can be none if not replacing an existing best route
    """
    network = update_message["network"]
    path = update_message["path"]
    come_from = update_message["come_from"]

    if come_from == "peer":
      locpref = 100
    elif come_from == "provider":
      locpref = 50
    elif come_from == "customer":
      locpref = 150

    new_route = {"path": path, "come_from": come_from, "LocPrf": locpref}

    if "aspv" in self.policy:
      new_route["aspv"] = self.aspv(new_route, update_message["src"])

    if self.aspv_local_prf:
      match new_route["aspv"]:
        case "Valid":
          new_route["LocPrf"] += 0
        case "Invalid":
          new_route["LocPrf"] += -25
        case "Unknown":
          new_route["LocPrf"] += -5

    try:
      new_route["best_path"] = False
      self.table[network].append(new_route)

      # select best path
      best = None
      for r in self.table[network]:
        if r["best_path"] == True:
          best = r
          break
      if best == None:
        raise BestPathNotExist

      for p in self.policy:
        if p == "LocPrf":
          if new_route["LocPrf"] > best["LocPrf"]:
            new_route["best_path"] = True
            best["best_path"] = False
            return (best, {"path": new_route["path"], "come_from": new_route["come_from"], "locPrf": new_route["LocPrf"], "network": network})
          elif new_route["LocPrf"] == best["LocPrf"]:
            continue
          elif new_route["LocPrf"] < best["LocPrf"]:
            return None
        elif p == "PathLength":
          new_length = len(new_route["path"].split("-"))
          best_length = len(best["path"].split("-"))
          if new_length < best_length:
            new_route["best_path"] = True
            best["best_path"] = False
            return (best, {"path": new_route["path"], "come_from": new_route["come_from"], "locPrf": new_route["LocPrf"], "network": network})
          elif new_length == best_length:
            continue
          elif new_length > best_length:
            return None
        elif p == "aspv":
          if new_route["aspv"] == "Invalid":
            return None

    except KeyError:
      if self.policy[0] == "aspv":
        if new_route["aspv"] == "Invalid":
          new_route["best_path"] = False
          self.table[network] = [new_route]
          return None
        else:
          new_route["best_path"] = True
          self.table[network] = [new_route]
          return (None, {"path": path, "come_from": come_from, "locPrf": new_route["LocPrf"], "network": network})
      elif self.aspv_local_prf and "aspv" in self.policy:
          if new_route["aspv"] == "Invalid":
            new_route["best_path"] = False
            self.table[network] = [new_route]
            return None
          else:
            new_route["best_path"] = True
            self.table[network] = [new_route]
            return (None, {"path": path, "come_from": come_from, "locPrf": new_route["LocPrf"], "network": network})
      else:
        new_route["best_path"] = True
        self.table[network] = [new_route]
        return (None, {"path": path, "come_from": come_from, "locPrf": new_route["LocPrf"], "network": network})

    except BestPathNotExist:
      if self.policy[0] == "aspv":
        if new_route["aspv"] == "Invalid":
          return None
        else:
          new_route["best_path"] = True
          return (None, {"path": path, "come_from": come_from, "locPrf": new_route["LocPrf"], "network": network})
      elif self.aspv_local_prf and "aspv" in self.policy:
        # automatically drop announcements for new routes which are invalid
        # skip straight to aspv, disregarding locPrf
        if new_route["aspv"] == "Invalid":
          return None
        else:
          new_route["best_path"] = True
          return (None, {"path": path, "come_from": come_from, "locPrf": new_route["LocPrf"], "network": network})
      else:
        new_route["best_path"] = True
        return (None, {"path": path, "come_from": come_from, "locPrf": new_route["LocPrf"], "network": network})

  def get_best_path_list(self):

    best_path_list = []

    for network in self.table.keys():
      for route in self.table[network]:
        if route["best_path"] == True:
          best_path_list.append(dict({"network": network}, **route))

    return best_path_list

  def get_table(self):
    return self.table

class LOTUSInputError(Exception):
  # Exception class for application-dependent error
  pass

class BestPathNotExist(Exception):
  pass

class Interpreter(Cmd):
  def __init__(self):
    super().__init__()
    self.as_class_list = AS_class_list()
    self.message_queue = queue.Queue()
    self.connection_list = []
    self.public_aspa_list = {}
    self.run_updates = {}

  intro = """
===^^^^^^^^^^^=============================================
=== \/ \ / \/ =============================================
== - \V V V/ - ============================================
= (( ( \ / ) )) ===========================================
====== LOTUS (Lightweight rOuTing simUlator with aSpa) ====
====== 2022 Naoki Umeda at Osaka University ===============
===========================================================
"""
  prompt = "LOTUS >> "

  def do_exit(self, line):
    return True

  def do_addAS(self, line):
    param = line.split()
    if len(param) == 1:
      if line.split()[0].isdecimal():
        self.as_class_list.add_AS(line)
    elif len(param) == 3:
      ls = line.split()
      if ls[0].isdecimal() and ls[2].isdecimal():
        self.as_class_list.add_AS(ls[0], ls[1], int(ls[2]))
    else:
      print("Usage: addAS [asn] [country] [rank]", file=sys.stderr)

  def do_showAS(self, line):
    if line.isdecimal():
      try:
        self.as_class_list.get_AS(line).show_info()
      except KeyError:
        print("Error: AS " + str(line) + " is NOT registered.", file=sys.stderr)
    else:
      print("Usage: showAS [asn]", file=sys.stderr)

  def do_showASList(self, line):

    param = line.split()

    sort_flag = False
    best_flag = False
    address = None
    try:
      if "sort" in param:
        sort_flag = True
        param.remove("sort")
      if "best" in param:
        best_flag = True
        param.remove("best")

      if len(param) == 0:
        address = None
      elif len(param) == 1 and re.fullmatch("((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])/[0-9][0-9]" , param[0]):
        address = param[0]
      else:
        raise LOTUSInputError

    except LOTUSInputError:
      print("Usage: showASList [sort] [best] [address]", file=sys.stderr)
      return

    self.as_class_list.show_AS_list(sort_flag, best_flag, address)

  def do_addMessage(self, line):
    try:
      if line == "":
        raise LOTUSInputError
      param = line.split()
      if len(param) == 2 and param[0] == "init" and param[1].isdecimal():          # ex) addMessage init 12
        self.message_queue.put({"type": "init", "src": str(param[1])})
      elif len(param) == 5 and param[0] == "update" and param[1].isdecimal() and \
           param[2].isdecimal() and re.fullmatch("((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])/[0-9][0-9]" , param[4]): # ex) addMessage update 12 34 54-12 10.1.1.0/24
        self.message_queue.put({"type": "update", "src": str(param[1]), "dst": str(param[2]), "path": str(param[3]), "network": str(param[4])})
      else:
        raise LOTUSInputError
    except LOTUSInputError:
      print("Usage: addMessage init [src_asn]", file=sys.stderr)
      print("       addMessage update [src_asn] [dst_asn] [path] [network]", file=sys.stderr)

  def do_addAllASInit(self, line):
    for as_number in self.as_class_list.get_AS_list().keys():
      self.message_queue.put({"type": "init", "src": as_number})

  def do_showMessage(self, line):
    tmp_queue = queue.Queue()
    while not self.message_queue.empty():
      q = self.message_queue.get()
      print(q)
      tmp_queue.put(q)
    self.message_queue = tmp_queue

  def do_addConnection(self, line):
    try:
      param = line.split()
      if len(param) == 3 and param[1].isdecimal() and param[2].isdecimal():
        if param[0] == "peer":
          self.connection_list.append({"type": "peer", "src": param[1], "dst": param[2]})
        elif param[0] == "down":
          self.connection_list.append({"type": "down", "src": param[1], "dst": param[2]})
        else:
          raise LOTUSInputError
      else:
        raise LOTUSInputError
    except LOTUSInputError:
      print("Usage: addConnection peer [src_asn] [dst_asn]", file=sys.stderr)
      print("       addConnection down [src_asn] [dst_asn]", file=sys.stderr)

  def do_showConnection(self, line):
    for c in self.connection_list:
      print(c)

  def do_addASPA(self, line):
    param = line.split()
    try:
      if len(param) < 2:
        raise LOTUSInputError
      else:
        for p in param:
          if not p.isdecimal():
            raise LOTUSInputError
      self.public_aspa_list[param[0]] = param[1:]
    except LOTUSInputError:
      print("Usage: addASPA [customer_asn] [provider_asns...]", file=sys.stderr)

  def do_showASPA(self, line):
    if line == "":
      print(self.public_aspa_list)
    else:
      try:
        print(self.public_aspa_list[line])
      except KeyError:
        print("Error: Unknown Syntax", file=sys.stderr)

  def do_setASPV(self, line):
    param = line.split()
    try:
      if len(param) < 2:
        raise LOTUSInputError
      if not param[0].isdecimal():
        raise LOTUSInputError
      as_class = self.as_class_list.get_AS(param[0])
      if param[1] == "on":
        if re.fullmatch("1|2|3", param[2]):
          if len(param) > 3:
            as_class.change_ASPV({"switch": "on", "priority": param[2], "aspv_local_prf": param[3]})
          else:
            as_class.change_ASPV({"switch": "on", "priority": param[2]})
        else:
          raise LOTUSInputError
      elif param[1] == "off":
        as_class.change_ASPV({"switch": "off"})
      else:
        raise LOTUSInputError

    except LOTUSInputError:
      print("Usage: setASPV [asn] on [1/2/3]", file=sys.stderr)
      print("       setASPV [asn] off", file=sys.stderr)
    except KeyError:
      print("Error: AS " + str(param[0]) + " is NOT registered.", file=sys.stderr)

  def get_connection_with(self, as_number):
    return (c for c in self.connection_list if as_number in (c["src"], c["dst"]))

  def as_a_is_what_on_c(self, as_a, connection_c):
    if connection_c["type"] == "peer":
      return "peer"
    elif connection_c["type"] == "down":
      if as_a == connection_c["src"]:
        return "provider"
      elif as_a == connection_c["dst"]:
        return "customer"

  def do_run(self, line):
    params = line.split()
    track_flag = False
    if len(params) > 0:
      if params[0] == "diff":
        track_flag = True
    for as_class in self.as_class_list.get_AS_list().values(): # To reference public_aspa_list when ASPV
      as_class.set_public_aspa(self.public_aspa_list)

    while not self.message_queue.empty():
      m = self.message_queue.get()
      if m["type"] == "update":
        as_class = self.as_class_list.get_AS(m["dst"])

        # search src-dst connection
        connection_with_dst = self.get_connection_with(m["dst"])
        connection = None
        for c in connection_with_dst:
          if m["src"] in [c["src"], c["dst"]]:
            connection = c
            break

        # peer, customer or provider
        m["come_from"] = self.as_a_is_what_on_c(m["src"], connection)

        update_result = as_class.update(m)
        if update_result == None:
          continue
        prev_best, route_diff = update_result
        if track_flag:
          if connection["dst"] not in self.run_updates:
            self.run_updates[connection["dst"]] = {}
          self.run_updates[connection["dst"]][route_diff["network"]] = (prev_best, route_diff)
        if route_diff["come_from"] == "customer":
          for c in connection_with_dst:
            new_update_message = {}
            new_update_message["type"] = "update"
            new_update_message["src"] = m["dst"]
            new_update_message["path"] = route_diff["path"]
            new_update_message["network"] = route_diff["network"]
            tmp = [c["src"], c["dst"]]
            tmp.remove(m["dst"])
            new_update_message["dst"] = tmp[0]
            self.message_queue.put(new_update_message)
        elif route_diff["come_from"] == "peer" or route_diff["come_from"] == "provider":
          for c in connection_with_dst:
            if c["type"] == "down" and c["src"] == m["dst"]:
              new_update_message = {}
              new_update_message["type"] = "update"
              new_update_message["src"] = m["dst"]
              new_update_message["dst"] = c["dst"]
              new_update_message["path"] = route_diff["path"]
              new_update_message["network"] = route_diff["network"]
              self.message_queue.put(new_update_message)

      elif m["type"] == "init":
        for c in self.get_connection_with(m["src"]):
          m["come_from"] = self.as_a_is_what_on_c(m["src"], c)
          tmp = [c["src"], c["dst"]]
          tmp.remove(m["src"])
          new_update_message_list = self.as_class_list.get_AS(tmp[0]).receive_init(m)
          for new_m in new_update_message_list:
            self.message_queue.put(dict({"type": "update"}, **new_m))

  def do_export(self, line):

    try:
      if line == "":
        raise LOTUSInputError
    except LOTUSInputError:
      print("Usage: export [filename]", file=sys.stderr)
      return

    export_content = {}

    export_content["AS_list"] = []
    class_list = self.as_class_list.get_AS_list()
    for v in class_list.values():
      export_content["AS_list"].append({"AS": v.as_number, "network_address": v.network_address, "policy": v.policy, "routing_table": v.routing_table.get_table()})

    export_content["IP_gen_seed"] = self.as_class_list.ip_gen.index

    export_content["message"] = []
    tmp_queue = queue.Queue()
    while not self.message_queue.empty():
      q = self.message_queue.get()
      export_content["message"].append(q)
      tmp_queue.put(q)
    self.message_queue = tmp_queue

    export_content["connection"] = self.connection_list

    export_content["ASPA"] = self.public_aspa_list

    with open(line, mode="w") as f:
      yaml.dump(export_content, f)

  def do_import(self, line):

    try:
      if line == "":
        raise LOTUSInputError
    except LOTUSInputError:
      print("Usage: import [filename]", file=sys.stderr)
      return

    try:
      with open(line, mode="r") as f:
        import_content = yaml.safe_load(f)
    except FileNotFoundError as e:
      print("Error: No such file or directory: " + line, file=sys.stderr)
      return

    self.as_class_list.import_AS_list(import_content["AS_list"])

    self.as_class_list.ip_gen.index = import_content["IP_gen_seed"]

    self.message_queue = queue.Queue()
    for m in import_content["message"]:
      self.message_queue.put(m)

    self.connection_list = import_content["connection"]

    self.public_aspa_list = import_content["ASPA"]

  def chain_search_ASPA(self, customer_as):

    try:
      prov_list = self.public_aspa_list[customer_as]
    except KeyError:
      return [customer_as]
    if str(prov_list[0]) == "0":
      return [customer_as]

    ret_list = []
    for prov in prov_list:
      ret_list.extend(self.chain_search_ASPA(prov))
    edited_list = [f"{ret}-{customer_as}" for ret in ret_list]
    return edited_list

  def do_genAttack(self, line):

    ASPA_utilize = False
    try:
      param = line.split()
      if "utilize" in param:
        ASPA_utilize = True
        param.remove("utilize")

      if len(param) != 2:
        raise LOTUSInputError
      elif not param[0].isdecimal() or not param[1].isdecimal():
        raise LOTUSInputError
    except LOTUSInputError:
      print("Usage: genAttack [utilize] [src_asn] [target_asn]", file=sys.stderr)
      return

    src = param[0]
    target = param[1]

    try:
      self.as_class_list.get_AS(src)
    except KeyError:
      print(f"Error: AS {src} is NOT registered.", file=sys.stderr)
      return

    try:
      target_as_class = self.as_class_list.get_AS(target)
    except KeyError:
      print(f"Error: AS {target} is NOT registered.", file=sys.stderr)
      return

    src_connection_list = self.get_connection_with(src)
    adj_as_list = []
    for c in src_connection_list:
      if src == c["src"]:
        adj_as_list.append(c["dst"])
      else:
        adj_as_list.append(c["src"])

    target_address = target_as_class.network_address

    attack_path_list = []
    if ASPA_utilize == True:
      generated_path = self.chain_search_ASPA(target)
      attack_path_list = [f"{src}-{path}" for path in generated_path]
    elif ASPA_utilize == False:
      attack_path_list.append(f"{src}-{target}")

    for path in attack_path_list:
      for adj_as in adj_as_list:
        self.message_queue.put({"type": "update", "src": str(src), "dst": str(adj_as), "path": path, "network": str(target_address)})

  def do_genOutsideAttack(self, line):

    ASPA_utilize = False
    try:
      param = line.split()
      if "utilize" in param:
        ASPA_utilize = True
        param.remove("utilize")

      if len(param) != 3 or not param[0].isdecimal() or not param[1].isdecimal() or not int(param[2]) == 1:
        raise LOTUSInputError
    except LOTUSInputError:
      print("Usage: genOutsideAttack [utilize] [via_asn] [target_asn] [hop_num=1]", file=sys.stderr)
      return

    via = param[0]
    target = param[1]

    try:
      self.as_class_list.get_AS(via)
    except KeyError:
      print(f"Error: AS {via} is NOT registered.", file=sys.stderr)
      return

    try:
      target_as_class = self.as_class_list.get_AS(target)
    except KeyError:
      print(f"Error: AS {target} is NOT registered.", file=sys.stderr)
      return

    outside_as = 64512  # Private AS Number
    while True:
      try:
        self.as_class_list.get_AS(str(outside_as))
        outside_as += 1
      except KeyError:
        break
    self.as_class_list.add_AS(str(outside_as))
    self.connection_list.append({"type": "down", "src": str(via), "dst": str(outside_as)})

    target_address = target_as_class.network_address

    attack_path_list = []
    if ASPA_utilize == True:
      generated_path = self.chain_search_ASPA(target)
      attack_path_list = [f"{outside_as}-{path}" for path in generated_path]
    elif ASPA_utilize == False:
      attack_path_list.append(f"{outside_as}-{target}")

    for path in attack_path_list:
      self.message_queue.put({"type": "update", "src": str(outside_as), "dst": str(via), "path": path, "network": str(target_address)})

  def do_autoASPA(self, line):

    param = line.split()
    try:
      if len(param) != 2 or not param[0].isdecimal() or not param[1].isdecimal():
        raise LOTUSInputError

      self.as_class_list.get_AS(param[0])  # Checking the AS is exist.

    except LOTUSInputError:
      print("Usage: autoASPA [asn] [hop_num]", file=sys.stderr)
      return
    except KeyError:
      print("Error: AS " + str(param[0]) + " is NOT registered.", file=sys.stderr)
      return

    customer_as_list = [param[0]]
    hop_number = int(param[1])

    while hop_number != 0 and len(customer_as_list) != 0:

      next_customer_as_list = []
      for customer_as in customer_as_list:
        c_list = self.get_connection_with(customer_as)

        provider_list = []
        for c in c_list:
          if self.as_a_is_what_on_c(customer_as, c) == "customer":
            provider_list.append(c["src"])

        next_customer_as_list += provider_list

        if len(provider_list) == 0:  # There is NOT provider AS.
          provider_list = [0]

        self.public_aspa_list[customer_as] = provider_list  # addASPA

      hop_number -= 1
      customer_as_list = list(set(next_customer_as_list))
  
  def execute(self, execution_lines):
    """
    executes the provided lines of lotus execution commands
    """
    self.cmdqueue.extend(execution_lines)
    while self.cmdqueue:
      line = self.cmdqueue.pop(0)
      line = self.precmd(line)
      stop = self.onecmd(line)
      stop = self.postcmd(stop, line)

  def exportIter(self, iterable, max_items, key, line, func=None):
    first = True
    for i in range(0, len(iterable), max_items):
      it = list(itertools.islice(iterable, i, i+max_items))
      if func:
        it = list(map(func, it))
      with open(line, mode="a") as f:
        if first:
          yaml.dump({key:it}, f)
        else:
          yaml.dump(it, f)

  def do_exportIter(self, line):
    """
    export the file iteratively
    intended for large export which would otherwise exhaust system resources
    """
    MAX_ITEMS = 1000
    try:
      if line == "":
        raise LOTUSInputError
    except LOTUSInputError:
      print("Usage: export [filename]", file=sys.stderr)
      return

    f = open(line, mode="w")
    f.close()

    def create_as_entry(v):
      return {"AS": v.as_number, "network_address": v.network_address, "policy": v.policy, "routing_table": v.routing_table.get_table()}
    
    self.exportIter(self.as_class_list.class_list.values(), MAX_ITEMS, "AS_list", line, func=create_as_entry)
    gc.collect()

    export_content = {}
    export_content["IP_gen_seed"] = self.as_class_list.ip_gen.index

    export_content["message"] = []
    tmp_queue = queue.Queue()
    first = True
    counter = 0
    while not self.message_queue.empty():
      q = self.message_queue.get()
      if first:
        export_content["message"].append(q)
      else:
        export_content.append(q)
      counter += 1
      if counter >= MAX_ITEMS:
        with open(line, mode="a") as f:
          yaml.dump(export_content, f)
        export_content = []
        first = False
        counter = 0
      tmp_queue.put(q)
    self.message_queue = tmp_queue

    if export_content:
      with open(line, mode="a") as f:
        yaml.dump(export_content, f)
    del export_content
    gc.collect()

    self.exportIter(self.connection_list, MAX_ITEMS, "connection", line)

    self.exportIter(self.public_aspa_list, MAX_ITEMS, "ASPA", line)
      

###
### MAIN PROGRAM
###

if __name__ == '__main__':
  execution_lines = []
  if len(sys.argv) > 1:
    target_file = sys.argv[1]
    if os.path.isfile(target_file):
      with open(target_file, 'r') as infile:
        execution_lines = infile.read().split('\n')
  try:
    interpreter = Interpreter()
    interpreter.cmdqueue.extend(execution_lines)
    interpreter.cmdloop()
  except KeyboardInterrupt:
    print("\nKeyboard Interrupt (Ctrl+C)")
    pass
  # except:
  #   pass
