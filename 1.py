class Node:
    def __init__(self, value, next=None):
        """
        Build one singly linked list node.
        Input: value, optional next node.
        Output: none; sets value and next fields.
        Locals: none.
        """
        self.value = value
        self.next = next

class LinkedList:
    def __init__(self):
        """
        Create an empty linked list.
        Input: none.
        Output: none; head starts as None.
        Locals: none.
        """
        self.head = None

    def append(self, value):
        """
        Append a new node with the given value at the end of the list.
        Input: value to store.
        Output: none; list grows by one node.
        Locals: newNode, current.
        """
        newNode = Node(value)
        if self.head is None:
            self.head = newNode
            return
        current = self.head
        while current.next:
            current = current.next
        current.next = newNode

def share_common_node(head1, head2):
    """
    Decide whether two singly linked lists share any Node by object identity.
    Input: head1, head2 (list heads, may be None).
    Output: True if some Node object appears on both lists, else False.
    Locals: seenNodes, current.
    """
    seenNodes = set()
    current = head1
    while current:
        seenNodes.add(current)
        current = current.next
    current = head2
    while current:
        if current in seenNodes:
            return True
        current = current.next
    return False

if __name__ == "__main__":
    listA = LinkedList()
    listA.append(1)
    listA.append(2)
    listA.append(3)

    listB = LinkedList()
    listB.append(1)
    listB.append(2)
    listB.append(3)

    sameValuesDifferentNodes = share_common_node(listA.head, listB.head)
    print("same values, different nodes:", sameValuesDifferentNodes)

    listC = LinkedList()
    listC.append(10)
    sharedNode = listA.head.next
    listC.head.next = sharedNode

    sharedByReference = share_common_node(listA.head, listC.head)
    print("shared node by reference:", sharedByReference)

    assert sameValuesDifferentNodes is False
    assert sharedByReference is True
    print("all tests passed")