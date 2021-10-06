/*
 * This code has been automatically generated by aas-core-csharp-codegen.
 * Do NOT edit or append.
 */

namespace AasCore.Aas3
{
    static class Visitation
    {
        /// <summary>
        /// Define the interface for a visitor which visits the instances of the model.
        /// </summary>
        public interface IVisitor<T>
        {
            public T Visit(IEntity entity);
            public T Visit(LangString langString);
            public T Visit(LangStringSet langStringSet);
            public T Visit(Identifier identifier);
            public T Visit(AdministrativeInformation administrativeInformation);
            public T Visit(Key key);
            public T Visit(Reference reference);
            public T Visit(AssetAdministrationShell assetAdministrationShell);
        }  // public interface IVisitor

        /// <summary>
        /// Provide a visitor that returns nothing and iterates over all the instances.
        /// </summary>
        /// <remarks>
        /// The visitor is based on the double-dispatch using <see cref="IEntity.Accept"> method.
        ///
        /// While meaningless on its own, extending this visitor is helpful if you only want 
        /// to implement a subset of visit methods, but still want to preserve deep iteration.
        /// </remarks> 
        public interface VoidVisitor : IVisitor<void>
        {
            public void Visit(IEntity entity)
            {
                // Dispatch
                entity.Accept(this);
            }

            public void Visit(LangString langString)
            {
                // Do nothing, but descend
                foreach (var something in langString.DescendOnce())
                {
                    something.Accept(this);
                }
            }

            public void Visit(LangStringSet langStringSet)
            {
                // Do nothing, but descend
                foreach (var something in langStringSet.DescendOnce())
                {
                    something.Accept(this);
                }
            }

            public void Visit(Identifier identifier)
            {
                // Do nothing, but descend
                foreach (var something in identifier.DescendOnce())
                {
                    something.Accept(this);
                }
            }

            public void Visit(AdministrativeInformation administrativeInformation)
            {
                // Do nothing, but descend
                foreach (var something in administrativeInformation.DescendOnce())
                {
                    something.Accept(this);
                }
            }

            public void Visit(Key key)
            {
                // Do nothing, but descend
                foreach (var something in key.DescendOnce())
                {
                    something.Accept(this);
                }
            }

            public void Visit(Reference reference)
            {
                // Do nothing, but descend
                foreach (var something in reference.DescendOnce())
                {
                    something.Accept(this);
                }
            }

            public void Visit(AssetAdministrationShell assetAdministrationShell)
            {
                // Do nothing, but descend
                foreach (var something in assetAdministrationShell.DescendOnce())
                {
                    something.Accept(this);
                }
            }
        }  // public class VoidVisitor
    }  // static class Visitation
}  // namespace AasCore.Aas3

/*
 * This code has been automatically generated by aas-core-csharp-codegen.
 * Do NOT edit or append.
 */
