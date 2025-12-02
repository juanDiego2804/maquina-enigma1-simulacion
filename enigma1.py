"""
Maquina enigma 1

Rotores:

rotor1:
EKMFLGDQVZNTOWYHXUSP
AIBRCJ
notch:Q

rotor2:
AJDKSIRUXBLHWTMCQGZN
PYFVOE
notch:E

rotor3:
BDFHJLCPRTXVZNYEIWGAK
MUSQO
notch:V

rotor4:
ESOVPZJAYQUIRHXLNFTGK
DCMWB
notch:J

rotor5:
VZBRGITYUPSDNHLXAWMJ
QOFEKC
notch:Z
"""
from typing import List

# Configuración por defecto: rotores I-II-III (izq->der), posiciones iniciales AAA, ring AAA, sin plugboard.
ROTOR1="EKMFLGDQVZNTOWYHXUSPAIBRCJ"
ROTOR2="AJDKSIRUXBLHWTMCQGZNPYFVOE"
ROTOR3="BDFHJLCPRTXVZNYEIWGAKMUSQO"
ROTOR4="ESOVPZJAYQUIRHXLNFTGKDCMWB"
ROTOR5="VZBRGITYUPSDNHLXAWMJQOFEKC"


# Un diccionario que mapea el nombre del rotor a su valor de notch correspondiente
NOTCHES_POR_ROTOR = {
    "EKMFLGDQVZNTOWYHXUSPAIBRCJ": "Q",
    "AJDKSIRUXBLHWTMCQGZNPYFVOE": "E",
    "BDFHJLCPRTXVZNYEIWGAKMUSQO": "V",
    "ESOVPZJAYQUIRHXLNFTGKDCMWB": "J",
    "VZBRGITYUPSDNHLXAWMJQOFEKC": "Z"
}

ALPH = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def char_to_idx(c: str) -> int:#convierte una letra a su indice (0-25)
    return ord(c) - ord('A')

def idx_to_char(i: int) -> str: #hace la operacion inversa y devuelve la letra
    return chr((i % 26) + ord('A'))

#wiring_str: string de 26 letras que describe el cableado físico del rotor (por ejemplo "EKMFLG...").
#self.wiring lo convierte a una lista de enteros 0..25 para manipularlo rápido.
class Rotor:
    def __init__(self, wiring_str: str, notch_letters: str, ring_setting: int=0, position: int=0):
        # wiring_str: 26-letter string, mapping from input index (0..25) to output letter
        self.wiring = [char_to_idx(c) for c in wiring_str]
        # inverse wiring: index -> which input produces that output
        self.inverse = [0]*26
        for i, out in enumerate(self.wiring):
            self.inverse[out] = i
        # notches: one or more letters where this rotor causes neighbor to step (e.g. "Q")
        self.notches = {char_to_idx(c) for c in notch_letters}
        self.ring = ring_setting % 26    # Ringstellung (0..25), default 0 means 'A'
        self.pos = position % 26         # self.pos: posición visible actual del rotor (A..Z → 0..25). Es lo que cambia cuando el rotor gira.
        

    def step(self):#gira el rotor una posición (incrementa pos).
        self.pos = (self.pos + 1) % 26

    def at_notch(self) -> bool:
        # return True if rotor's current position equals a notch position
        return self.pos in self.notches

    def forward(self, in_idx: int) -> int:
        """
        Paso en sentido derecha->izquierda (entrada en cara derecha).
        Fórmula (0-based):
            step = (in_idx + pos - ring) % 26: aplica los offsets físicos: la entrada se desplaza según la rotación del rotor y el ring setting. Esto encuentra el contacto físico en el cableado interno.

letter_idx = self.wiring[step]: lee qué salida interna corresponde a ese contacto.

out_idx = (letter_idx - pos + ring) % 26: deshace el desplazamiento para devolver la letra al sistema exterior (y pasa al siguiente rotor).

Esta fórmula implementa exactamente el ajuste: sumar posición antes de consultar wiring y restarla antes de salir.
        """
        step = (in_idx + self.pos - self.ring) % 26
        letter_idx = self.wiring[step]
        out_idx = (letter_idx - self.pos + self.ring) % 26
        return out_idx

    def backward(self, in_idx: int) -> int:#la misma idea pero para la vuelta desde el reflector (sentido izquierda→derecha).
        """
        Paso en sentido izquierda->derecha (vuelta desde reflector).
        Fórmula (0-based):
            step = (in_idx + pos - ring) % 26
            k = inverse[step]   # tal que wiring[k] == step
            out_idx = (k - pos + ring) % 26
        """
        step = (in_idx + self.pos - self.ring) % 26
        k = self.inverse[step]
        out_idx = (k - self.pos + self.ring) % 26
        return out_idx

class EnigmaMachine:
    def __init__(self, left: Rotor, middle: Rotor, right: Rotor, reflector_wiring: str, plugboard_map=None):
        self.left = left
        self.middle = middle
        self.right = right
        self.reflector = [char_to_idx(c) for c in reflector_wiring]
        # plugboard as dict mapping index->index; default identity
        if plugboard_map is None:
            self.plug = {i:i for i in range(26)}
        else:
            # plugboard_map expected like {"A":"D", "D":"A", ...}
            self.plug = {i:i for i in range(26)}
            for a,b in plugboard_map.items():
                ia = char_to_idx(a)
                ib = char_to_idx(b)
                self.plug[ia] = ib
                self.plug[ib] = ia

    """
    Esta función implementa la secuencia de avance (incluyendo el double-step).

    Primero guarda las posiciones antiguas (right_old, mid_old, left_old) porque la decisión de qué rotores deben avanzar se basa en los valores antes de girar.

    left_should = (mid_old in self.middle.notches):

    Si el rotor medio estaba en una posición de notch antes de la pulsación, entonces el izquierdo debe avanzar (esta es la parte que provoca double-step).

    mid_should = (mid_old in self.middle.notches) or (right_old in self.right.notches):

    El medio avanzará si estaba en notch (esto dispara al izquierdo) o si el rotor derecho estaba en notch (el derecho empuja al medio).

    Aplicación de los pasos:

    Si left_should → se gira el rotor izquierdo.

    Si mid_should → se gira el rotor medio.

    Finalmente, el rotor derecho siempre avanza.

    Nota: primero se gira el izquierdo si corresponde, luego el medio, y al final el derecho. Este orden es importante para reproducir el comportamiento mecánico del double-step exactamente como en la máquina real."""
    def step_rotors(self):
        # Implementación según la regla discutida (usa posiciones old para comprobar notches)
        right_old = self.right.pos
        mid_old = self.middle.pos
        left_old = self.left.pos

        # Decide qué rotors deben avanzar (double-step behavior)
        left_should = (mid_old in self.middle.notches)
        mid_should = (mid_old in self.middle.notches) or (right_old in self.right.notches)

        # Aplica avances: importante seguir orden adecuado
        if left_should:
            self.left.step()
        if mid_should:
            self.middle.step()
        # Right siempre avanza 1
        self.right.step()

    def encrypt_letter(self, ch: str) -> str:
        # Sólo letras A-Z esperadas (mayúsculas), si es numero o caracter especial lo ignora
        if not ('A' <= ch <= 'Z'):
            return ch

        # 1) stepping
        self.step_rotors()

        # 2) plugboard in
        idx = char_to_idx(ch)
        idx = self.plug[idx]

        # 3) forward rotors (right -> left)
        idx = self.right.forward(idx)
        idx = self.middle.forward(idx)
        idx = self.left.forward(idx)

        # 4) reflector
        idx = self.reflector[idx]

        # 5) backward rotors (left -> right)
        idx = self.left.backward(idx)
        idx = self.middle.backward(idx)
        idx = self.right.backward(idx)

        # 6) plugboard out
        idx = self.plug[idx]

        return idx_to_char(idx)

    def encrypt_text(self, text: str) -> str:
        out = []
        for ch in text:
            if 'A' <= ch <= 'Z':
                out.append(self.encrypt_letter(ch))
            else:
                # ignoramos/omitir o podrías preservar separadores; aquí eliminamos no-letras
                pass
        return "".join(out)

def build_machine(rotor_left,rotor_mid,rotor_right):
    # Rotores 1-3 izq,derecha     
    wiring_I   = rotor_left
    notch_I    = NOTCHES_POR_ROTOR[rotor_left]
    wiring_II  = rotor_mid
    notch_II   = NOTCHES_POR_ROTOR[rotor_mid]
    wiring_III = rotor_right
    notch_III  = NOTCHES_POR_ROTOR[rotor_right]
    
    reflector_B = "YRUHQSLDPXNGOKMIEBFZCWVJAT"

    # Ring settings A A A -> 0, positions A A A -> 0
    rotor_left  = Rotor(wiring_I, notch_I, ring_setting=0, position=0)   # Rotor I (izq)
    rotor_mid   = Rotor(wiring_II, notch_II, ring_setting=0, position=0)  # Rotor II (medio)
    rotor_right = Rotor(wiring_III, notch_III, ring_setting=0, position=0) # Rotor III (der)

    return EnigmaMachine(rotor_left, rotor_mid, rotor_right, reflector_B, plugboard_map=None)

if __name__ == "__main__":
    machine = build_machine(ROTOR1,ROTOR2,ROTOR3)

    raw = input("Introduce el texto a encriptar (se usarán sólo letras A-Z):\n> ")
    # normalizar: mayúsculas y eliminar no-letras
    normalized = "".join([c for c in raw.upper() if 'A' <= c <= 'Z'])
    if len(normalized) == 0:
        print("No se encontró texto válido (A-Z).")
    else:
        ciphertext = machine.encrypt_text(normalized)
        print("\nTexto normalizado (A-Z):", normalized)
        print("Texto cifrado:           ", ciphertext)