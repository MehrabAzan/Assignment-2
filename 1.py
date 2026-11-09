class Node:
    def __init__(self, value, next=None):
        self.value = value
        self.next = next

class LinkedList:
    # Constructor.
    def __init__(self):
        # The first node in the linked list.
        # The head is either a Node object or None if the list is empty.
        self.head = None

    # Method. Adds a node with specified value to the end of the list.
    def append(self, value):
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
    Return True if the two linked lists share any Node by identity (reference),
    not by value.

    Collects node references from the first list in a set, then scans the second
    list for membership. Time: O(n). Space: O(n).
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